"""
Workflow Runner — the execution engine for workflow definitions.

Runs a workflow's steps in order, threading each step's output into a variable
namespace that later steps interpolate with {{name}} templates. Step kinds:

  - tool:     call an MCP tool (deterministic; no LLM)         -> ToolBroker
  - prompt:   an ISOLATED LLM call over only the workflow's own
              context — no main-brain memory, personality, or
              conversation, and no tools. A pure text transform.
  - speak:    say the interpolated text aloud via the voice
              assistant (delivery.send_voice); no LLM
  - shell:    run an arbitrary shell command on this machine
              (deterministic; no LLM). UNRESTRICTED by request —
              no command allow/deny list, runs as your user.
              {{vars}} interpolate into the command line; the
              combined stdout+stderr is the step's output.
  - extract:  isolated LLM call that pulls named fields out of
              text and injects them as variables
  - stop:     end the workflow early when a condition passes
  - workflow: run another workflow (composition, recursive)
  - foreach:  run a nested list of steps once per item of a list
              (a JSON array or newline/comma-separated text) —
              the workflow's for-loop

Only the final output is returned to the caller. Nothing about a prompt step's
reasoning leaks back into the main brain — the brain sees a workflow as a single
tool that takes params and returns a string.

The runner is deliberately NOT the main AgentCore loop: chaining heavy steps
(each its own tool call) inside the brain's 25-round budget would burn context.
Here a thin sequencer advances the steps and only calls the LLM where a `prompt`
step actually needs judgment.
"""

import asyncio
import json
import os
import re
from datetime import datetime, timedelta

import config
import delivery
import workflow_store as store
from skills.mcp_client import MCPClient

# Dots allowed so trigger payloads can be referenced by path ({{payload.event}});
# the trigger engine flattens webhook JSON into dotted variable names.
_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
_MAX_DEPTH = 5


class WorkflowError(Exception):
    """Any authoring/runtime problem worth surfacing to the caller verbatim."""


def _make_adapter():
    """Fresh, standalone LLM adapter for isolated prompt steps. Deliberately
    does NOT import AgentCore/MemoryManager — a prompt step must not touch the
    brain's memory or conversation."""
    if config.LLM_PROVIDER == "claude":
        from adapters.claude import ClaudeAdapter
        return ClaudeAdapter()
    from adapters.openrouter import OpenRouterAdapter
    return OpenRouterAdapter()


def _builtins() -> dict:
    now = datetime.now()
    return {
        "today": now.strftime("%Y-%m-%d"),
        "yesterday": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
        "tomorrow": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        "now": now.strftime("%Y-%m-%d %H:%M"),
        "time": now.strftime("%I:%M %p"),
        "weekday": now.strftime("%A"),
    }


def _interp(text: str, variables: dict) -> str:
    """Replace {{name}} with str(variables[name]). Unknown names raise, so a
    typo in a template fails loudly at authoring time instead of silently
    passing a literal '{{foo}}' to a tool."""
    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key not in variables:
            raise WorkflowError(
                f"unknown variable '{{{{{key}}}}}'. Available: {', '.join(sorted(variables))}"
            )
        return str(variables[key])
    return _VAR_RE.sub(repl, text)


def _interp_value(value, variables: dict):
    """Interpolate templates anywhere inside a step's args (strings, nested
    dicts, lists). Non-strings (ints, bools) pass through untouched."""
    if isinstance(value, str):
        return _interp(value, variables)
    if isinstance(value, dict):
        return {k: _interp_value(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_interp_value(v, variables) for v in value]
    return value


def _operand(raw: str, variables: dict) -> str:
    """Interpolate one side of a condition and strip whitespace + optional quotes."""
    val = _interp(raw, variables).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    return val


def _eval_when(expr: str, variables: dict) -> bool:
    """Evaluate a tiny, deterministic condition language (no LLM):

        X == Y | X != Y | X contains Y | X not contains Y
        X is empty | X is not empty | X > Y | X < Y

    The OPERATOR is parsed from the authored expression BEFORE interpolation, so
    tool output containing words like 'contains' can't break parsing. ==/!= and
    contains are case-insensitive; >/< require numbers. Unrecognized expressions
    raise, so a typo'd condition fails loudly instead of silently running/skipping."""
    raw = (expr or "").strip()
    m = re.match(r"^(.*?)\s+is\s+not\s+empty$", raw, re.I)
    if m:
        return _operand(m.group(1), variables) != ""
    m = re.match(r"^(.*?)\s+is\s+empty$", raw, re.I)
    if m:
        return _operand(m.group(1), variables) == ""
    m = re.match(r"^(.*?)\s+(not\s+contains|contains)\s+(.*)$", raw, re.I)
    if m:
        left = _operand(m.group(1), variables).lower()
        right = _operand(m.group(3), variables).lower()
        hit = right in left
        return (not hit) if m.group(2).lower().startswith("not") else hit
    m = re.match(r"^(.*?)\s*(==|!=)\s*(.*)$", raw)
    if m:
        left = _operand(m.group(1), variables)
        right = _operand(m.group(3), variables)
        try:
            eq = float(left) == float(right)
        except ValueError:
            eq = left.lower() == right.lower()
        return eq if m.group(2) == "==" else not eq
    m = re.match(r"^(.*?)\s*(>|<)\s*(.*)$", raw)
    if m:
        left, right = _operand(m.group(1), variables), _operand(m.group(3), variables)
        try:
            lf, rf = float(left), float(right)
        except ValueError:
            raise WorkflowError(f"'{m.group(2)}' needs numbers, got {left!r} and {right!r}")
        return lf > rf if m.group(2) == ">" else lf < rf
    raise WorkflowError(
        f"can't parse condition {raw!r}. Use: X == Y, X != Y, X contains Y, "
        "X not contains Y, X is empty, X is not empty, X > Y, X < Y"
    )


# The shell step is UNRESTRICTED by request: no command allow/deny list and no
# repo self-protection. It runs whatever it's given, as the user this process
# runs as. `timeout` and the output cap below are NOT safety rails — they only
# keep a runaway command from hanging the workflow or flooding the trace; the
# command itself is never inspected or blocked.
_SHELL_TIMEOUT_DEFAULT = 30
_SHELL_TIMEOUT_MAX = 120
_SHELL_OUTPUT_CAP = 8000


async def _run_shell(command: str, cwd: str | None, timeout: float) -> str:
    """Run a command via the shell, capturing combined stdout+stderr. Always
    returns text (prefixed with the exit code on failure) rather than raising,
    so a failed command is a normal — inspectable — step output, not a workflow
    crash; the workflow author decides via `when` whether to react to it."""
    run_cwd = os.path.expanduser(cwd) if cwd else os.path.expanduser("~")
    try:
        proc = await asyncio.create_subprocess_shell(
            command, cwd=run_cwd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return f"[ERROR] command timed out after {timeout}s: {command!r}"
    except OSError as e:
        return f"[ERROR] failed to start command: {e}"

    text = out.decode("utf-8", errors="replace")
    if len(text) > _SHELL_OUTPUT_CAP:
        text = text[:_SHELL_OUTPUT_CAP] + "\n[...truncated]"
    if proc.returncode != 0:
        return f"[ERROR] exit code {proc.returncode}\n{text}"
    return text or "(no output)"


class ToolBroker:
    """Lazily starts (and caches) the MCP server subprocesses referenced by a
    workflow's tool steps, using the exact command/args/env from config. One
    broker is shared across a top-level run and its sub-workflows, then closed
    when the top-level run finishes. Only the servers a workflow actually uses
    are started — not the whole fleet."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}

    async def _client(self, server: str) -> MCPClient:
        if server in self._clients:
            return self._clients[server]
        cfg = config.MCP_SERVERS.get(server)
        if not cfg:
            raise WorkflowError(f"no MCP server configured named '{server}'")
        client = MCPClient(server, cfg["command"], cfg["args"], cfg.get("env"))
        await client.start()
        await client.list_tools()  # populate cache so argument type-coercion works
        self._clients[server] = client
        return client

    async def call(self, namespaced: str, args: dict) -> str:
        if "__" not in namespaced:
            raise WorkflowError(f"tool must be namespaced (server__tool): got '{namespaced}'")
        server, tool = namespaced.split("__", 1)
        client = await self._client(server)
        return await client.call_tool(tool, args)

    async def close(self):
        for c in self._clients.values():
            try:
                await c.stop()
            except Exception:
                pass
        self._clients.clear()


class RouterBroker:
    """Tool access that reuses an ALREADY-RUNNING ToolRouter's MCP clients rather
    than starting its own. Used when a workflow is invoked in-process by the agent
    (AgentCore intercepts run_workflow): this avoids spawning duplicate child
    servers, which can deadlock on shared resources (e.g. the Cync token lock) and
    hang the tool call — and thus the whole agent."""

    def __init__(self, router):
        self._router = router

    async def call(self, namespaced: str, args: dict) -> str:
        return await self._router.call_tool(namespaced, args)

    async def close(self):
        pass  # not ours to tear down — the agent owns these clients


_PROMPT_SYSTEM = (
    "You are one step inside an automated workflow. You are given some context and an "
    "instruction. Follow the instruction using ONLY the provided context. Respond with "
    "just the requested output — no preamble, no explanations, no meta-commentary."
)


async def _run_prompt(adapter, text: str, model: str | None = None) -> str:
    """Isolated LLM call: a single user message, a minimal system prompt, no
    tools, no history. Its reasoning never re-enters the main conversation.
    An optional per-step `model` picks a different OpenRouter model for this call."""
    resp = await adapter.chat(_PROMPT_SYSTEM, [{"role": "user", "content": text}], None, model=model)
    return (resp.text or "").strip()


_EXTRACT_SYSTEM = (
    "You extract structured data from text. Respond with a SINGLE valid JSON object "
    "and nothing else — no prose, no explanation, no code fences."
)


async def _run_extract(adapter, input_text: str, fields: list, model: str | None = None) -> dict:
    """Ask the LLM to pull the requested fields out of `input_text` as a JSON object
    (isolated call — no tools, no history). Returns the parsed object; raises if the
    model doesn't return usable JSON so the failure is visible in the test trace."""
    field_lines = "\n".join(
        f'- "{f["id"]}": {f.get("description", "")}'
        for f in fields if f.get("id")
    )
    prompt = (
        "Extract these fields from the text and respond with ONLY a JSON object "
        "using exactly these keys:\n"
        f"{field_lines}\n\n"
        "Use the most natural JSON type for each value (string, number, boolean, "
        "array). If a field isn't present in the text, use null.\n\n"
        f"Text:\n{input_text}"
    )
    resp = await adapter.chat(_EXTRACT_SYSTEM, [{"role": "user", "content": prompt}], None, model=model)
    data = _parse_json_object((resp.text or "").strip())
    if data is None:
        raise WorkflowError(
            f"extract step: model did not return a JSON object. Got: {(resp.text or '')[:300]!r}"
        )
    return data


def _parse_json_object(raw: str) -> dict | None:
    """Best-effort parse of a JSON object out of an LLM response — tolerant of code
    fences and surrounding reasoning text."""
    s = raw.strip()
    if s.startswith("```"):
        s = "\n".join(l for l in s.splitlines() if not l.strip().startswith("```"))
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        obj = json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _as_var(value) -> str:
    """Normalize an extracted JSON value into the string form the variable system
    uses. Booleans become 'true'/'false' (so tool-arg coercion re-types them),
    numbers/strings pass through, and objects/arrays are re-serialized as JSON."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (int, float, str)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


# A foreach over more items than this is almost certainly a template bug (e.g.
# iterating a whole document line-by-line), and each item can cost a tool/LLM
# call — fail loudly instead of grinding.
_MAX_LOOP_ITEMS = 100


def _parse_items(raw: str) -> list[str]:
    """Turn a foreach `items` string into a list. Accepts, in order of
    preference: a JSON array (each element normalized via _as_var), one item
    per non-empty line, or a single comma-separated line. Step outputs are
    strings, so this is how a grep result, an extract'ed array, or a hand-typed
    'a, b, c' all become iterable without the author caring which they have."""
    s = (raw or "").strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            arr = json.loads(s)
        except json.JSONDecodeError:
            arr = None
        if isinstance(arr, list):
            return [_as_var(v) for v in arr]
    lines = [l.strip() for l in s.splitlines() if l.strip()]
    if len(lines) == 1 and "," in lines[0]:
        return [p.strip() for p in lines[0].split(",") if p.strip()]
    return lines


async def _run_steps(
    steps: list, variables: dict, *, defn: dict,
    broker, adapter, trace, on_event, depth: int, id_prefix: str = "",
) -> tuple[str, str | None]:
    """Run a list of steps in order against a shared variable namespace.

    Returns (last_output, stop_output). stop_output is None unless a stop step
    fired — in which case it is the workflow's final output, and it propagates
    up through any enclosing foreach: a stop ends the WHOLE workflow, not just
    the current loop iteration (skip-an-item is what per-step `when` is for).

    `id_prefix` namespaces the positional stepN variables of a foreach body
    ({{mylist.step1}} etc.) so they can't shadow the top level's {{step1}};
    explicit ids are always used verbatim.
    """
    last = ""
    for i, step in enumerate(steps, 1):
        sid = step.get("id") or f"{id_prefix}step{i}"
        kind = next((k for k in ("tool", "prompt", "speak", "shell", "extract", "workflow", "stop", "foreach") if k in step), "?")
        label = {"tool": step.get("tool", ""), "prompt": "Prompt", "speak": "Speak",
                 "shell": "Shell", "extract": "Extract", "stop": "Stop",
                 "workflow": f"Workflow: {step.get('workflow', '')}",
                 "foreach": "Loop"}.get(kind, "?")

        # Guard: a step with `when` runs only if the condition passes. A skipped
        # step's variable is set to "" so later {{refs}} don't hard-fail.
        when = step.get("when")
        if when and not _eval_when(when, variables):
            variables[sid] = variables[f"{id_prefix}step{i}"] = ""
            if on_event:
                on_event({"type": "skip", "index": i, "depth": depth,
                          "id": sid, "kind": kind, "label": label})
            if trace is not None:
                trace.append({"step": sid, "kind": kind, "output": "[skipped — when false]"})
            continue

        if on_event:
            on_event({"type": "start", "index": i, "depth": depth,
                      "id": sid, "kind": kind, "label": label})

        # Stop node: end the workflow early with its own output (early exit /
        # guard clause). Its inner `when` gates the stop itself.
        if kind == "stop":
            spec = step["stop"] or {}
            scond = spec.get("when")
            if scond and not _eval_when(scond, variables):
                variables[sid] = variables[f"{id_prefix}step{i}"] = ""
                if trace is not None:
                    trace.append({"step": sid, "kind": "stop", "output": "[stop not triggered]"})
                continue
            stop_out = spec.get("output")
            final = _interp(str(stop_out), variables) if stop_out else last
            if not (final or "").strip():
                final = f"Workflow '{defn.get('name', '?')}' stopped at step {i}."
            if trace is not None:
                trace.append({"step": sid, "kind": "stop", "output": final[:2000]})
            return last, final

        if "tool" in step:
            args = _interp_value(step.get("args") or {}, variables)
            out = await broker.call(step["tool"], args)
        elif "prompt" in step:
            out = await _run_prompt(adapter, _interp(step["prompt"], variables),
                                    model=step.get("model"))
        elif "speak" in step:
            # Side-effect step: the spoken text is also the step's output, so
            # later steps (and the default final output) can reference it.
            # send_voice is best-effort by design, so surface its False here —
            # a speak step that didn't speak must fail, not pretend.
            out = _interp(str(step["speak"]), variables)
            if not await delivery.send_voice(out):
                raise WorkflowError(
                    f"step {i} ('{sid}'): voice assistant unreachable — nothing was spoken"
                )
        elif "shell" in step:
            spec = step["shell"] or {}
            command = _interp(str(spec.get("command", "")), variables)
            cwd = _interp(str(spec.get("cwd", "")), variables) if spec.get("cwd") else None
            timeout = min(float(spec.get("timeout") or _SHELL_TIMEOUT_DEFAULT), _SHELL_TIMEOUT_MAX)
            out = await _run_shell(command, cwd, timeout)
        elif "extract" in step:
            spec = step["extract"] or {}
            input_text = _interp(str(spec.get("input", "")), variables)
            fields = spec.get("fields") or []
            extracted = await _run_extract(adapter, input_text, fields, model=step.get("model"))
            # Inject each extracted field as its own variable, referenceable as
            # {{id}} by any later step (and coerced to the right type at the
            # tool boundary). The step's own output is the raw JSON.
            for f in fields:
                fid = f.get("id")
                if fid:
                    variables[fid] = _as_var(extracted.get(fid, ""))
            out = json.dumps(extracted, ensure_ascii=False)
        elif "foreach" in step:
            out = await _run_foreach(
                step, sid, i, variables, defn=defn, broker=broker,
                adapter=adapter, trace=trace, on_event=on_event, depth=depth,
            )
            if isinstance(out, tuple):  # a stop fired inside the loop body
                return last, out[0]
        elif "workflow" in step:
            sub_args = _interp_value(step.get("args") or {}, variables)
            out = await run_workflow(
                step["workflow"], sub_args,
                broker=broker, adapter=adapter, trace=trace,
                on_event=on_event, _depth=depth + 1,
            )
        else:
            raise WorkflowError(f"step {i} ('{sid}') has no tool|prompt|speak|shell|workflow|extract|stop|foreach key")

        out = out if isinstance(out, str) else str(out)
        variables[sid] = out
        variables[f"{id_prefix}step{i}"] = out
        last = out
        if trace is not None:
            trace.append({"step": sid, "kind": kind, "output": out[:2000]})

    return last, None


async def _run_foreach(
    step: dict, sid: str, index: int, variables: dict, *,
    defn: dict, broker, adapter, trace, on_event, depth: int,
) -> str | tuple:
    """Execute a foreach step: run its nested steps once per item.

        {"foreach": {"items": "{{ids}}", "as": "id", "join": "\\n", "steps": [...]}}

    `items` is a JSON array, newline-separated text, or one comma-separated
    line (so a tool/shell/extract output iterates without reshaping). Each
    iteration sets {{<as>}} (default {{item}}), {{loop_index}} (1-based) and
    {{loop_total}}; body steps share the workflow's namespace, so extract
    fields and explicit ids written in one iteration are visible to the next.
    Returns the per-iteration last outputs joined with `join` (default one per
    line) — or a 1-tuple carrying a stop step's final output, which the caller
    unwraps and propagates (a plain str is a normal output; the tuple is the
    only out-of-band shape _run_steps can't mistake for one)."""
    spec = step["foreach"] or {}
    body = spec.get("steps") or []
    if not body:
        raise WorkflowError(f"step {index} ('{sid}'): foreach needs a non-empty 'steps' list")

    raw_items = spec.get("items", "")
    if isinstance(raw_items, list):
        items = [_as_var(v) for v in _interp_value(raw_items, variables)]
    else:
        items = _parse_items(_interp(str(raw_items), variables))
    if len(items) > _MAX_LOOP_ITEMS:
        raise WorkflowError(
            f"step {index} ('{sid}'): foreach got {len(items)} items (max {_MAX_LOOP_ITEMS})"
        )

    as_name = str(spec.get("as") or "item").strip() or "item"
    outs = []
    for n, item in enumerate(items, 1):
        variables[as_name] = item
        variables["loop_index"] = str(n)
        variables["loop_total"] = str(len(items))
        if on_event:
            on_event({"type": "start", "index": index, "depth": depth,
                      "id": sid, "kind": "foreach",
                      "label": f"Loop {n}/{len(items)}: {as_name}={item[:60]}"})
        it_last, it_stop = await _run_steps(
            body, variables, defn=defn, broker=broker, adapter=adapter,
            trace=trace, on_event=on_event, depth=depth + 1,
            id_prefix=f"{sid}.",
        )
        if it_stop is not None:
            return (it_stop,)
        outs.append(it_last)

    join = spec.get("join")
    return ("\n" if join is None else str(join)).join(outs)


async def run_workflow(
    name_or_defn,
    params: dict | None = None,
    *,
    broker: ToolBroker | None = None,
    adapter=None,
    trace: list | None = None,
    on_event=None,
    _depth: int = 0,
) -> str:
    """Run a workflow and return ONLY its final output string.

    Args:
        name_or_defn: a workflow name (looked up in the store) or a full defn dict.
        params: parameter values.
        broker/adapter: shared across composed sub-workflows; created if omitted.
        trace: if provided, appended with a per-step record (for logging/debug).
    """
    if _depth > _MAX_DEPTH:
        raise WorkflowError(f"workflow nesting exceeded {_MAX_DEPTH} levels")

    defn = store.get_workflow(name_or_defn) if isinstance(name_or_defn, str) else name_or_defn
    if not defn:
        raise WorkflowError(f"no workflow named '{name_or_defn}'")

    own_broker = broker is None
    broker = broker or ToolBroker()
    adapter = adapter or _make_adapter()
    params = params or {}

    try:
        variables = _builtins()

        # Resolve declared params: use the provided value, else the (interpolated)
        # default, else "" — enforcing required. Missing required params are
        # collected and reported together, with the full spec and a ready-to-use
        # example, so the caller (usually the agent) can fix the call in one retry.
        missing = []
        for p in defn.get("params", []) or []:
            pname = p["name"]
            if pname in params and params[pname] not in (None, ""):
                variables[pname] = params[pname]
            elif "default" in p:
                variables[pname] = _interp(str(p["default"]), variables)
            elif p.get("required"):
                missing.append(p)
            else:
                variables[pname] = ""
        if missing:
            spec = "; ".join(
                p["name"] + (f" — {p['description']}" if p.get("description") else "")
                for p in missing
            )
            example = json.dumps({p["name"]: f"<{p['name']}>" for p in missing})
            raise WorkflowError(
                f"workflow '{defn.get('name', '?')}' requires params you did not "
                f"provide: {spec}. Retry with a params JSON object, e.g. "
                f"params='{example}'."
            )

        # Expose any extra provided params verbatim (without shadowing built-ins).
        for k, v in params.items():
            variables.setdefault(k, v)

        last, stopped = await _run_steps(
            defn.get("steps", []), variables, defn=defn,
            broker=broker, adapter=adapter, trace=trace,
            on_event=on_event, depth=_depth,
        )
        if stopped is not None:
            return stopped

        output_tmpl = defn.get("output")
        final = _interp(output_tmpl, variables) if output_tmpl else last
        if not (final or "").strip():
            # Never hand back an empty string (e.g. an actuator workflow whose last
            # step returns nothing) — it reads as "no result" and can leave the
            # agent unsure the run finished. Return a clear completion summary.
            final = (f"Workflow '{defn.get('name', '?')}' completed "
                     f"{len(defn.get('steps', []))} step(s) with no text output.")
        return final
    finally:
        if own_broker:
            await broker.close()
