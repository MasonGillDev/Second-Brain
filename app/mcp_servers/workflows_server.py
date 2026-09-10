"""
Workflows MCP Server.

The agent's interface to the workflow registry: author, inspect, and run named
workflows. Definitions live in workflow_store; execution is delegated to
workflow_runner, which runs each workflow in its OWN context — tool steps call
MCP tools directly and `prompt` steps make isolated LLM calls that never touch
the main brain's memory or conversation. The agent only ever receives a
workflow's final output.

The same runner module is imported by the scheduler daemon, so a workflow can be
triggered by the agent (this server) or by cron (scheduler) without duplication.
"""

import sys
import os
import json

# Add project root (app/) to path so we can import the shared modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

import workflow_store as store
import workflow_runner as runner

mcp = FastMCP("workflows")


@mcp.tool()
def create_workflow(definition: str) -> str:
    """
    Create or update a workflow from a JSON definition.

    `definition` is a JSON object:
      {
        "name": "snake_case_name",
        "description": "One line: what it does and when to run it.",
        "params": [
          {"name": "date", "required": false, "default": "{{today}}", "description": "..."}
        ],
        "steps": [
          {"id": "events", "tool": "calendar__get_day", "args": {"date": "{{date}}"}},
          {"id": "brief",  "prompt": "Summarize into a brief:\n{{events}}"},
          {"workflow": "other_workflow", "args": {"x": "{{events}}"}}
        ],
        "output": "{{brief}}",
        "surfaces": {"schedulable": true, "expose_as_tool": true}
      }

    Each step is EXACTLY ONE of:
      - tool:     {"tool": "server__tool_name", "args": {...}}   deterministic MCP call
      - prompt:   {"prompt": "text with {{vars}}"}               isolated LLM transform (no tools)
      - speak:    {"speak": "text with {{vars}}"}                say the text aloud through the
                  voice assistant (no LLM). The step's output is the spoken text; it FAILS
                  if the voice service is unreachable
      - shell:    {"shell": {"command": "text with {{vars}}", "cwd": "~/optional", "timeout": 30}}
                  run a shell command on this machine (no LLM). UNRESTRICTED — no
                  command allow/deny list, runs as your user. Output is stdout+stderr
                  (prefixed with the exit code on failure). timeout defaults to 30s,
                  capped at 120s — for anything longer use the code skill's
                  run_background instead
      - workflow: {"workflow": "name", "args": {...}}            run another workflow
      - extract:  {"extract": {"input": "{{step1}}", "fields": [{"id": "x", "description": "..."}]}}
                  isolated LLM call that pulls structured data out of `input` and
                  injects each field id as a variable ({{x}}) for later steps to use
      - stop:     {"stop": {"when": "{{x}} is empty", "output": "Nothing to do."}}
                  end the workflow early with `output` when the condition passes
                  (omit "when" to always stop; omit "output" to return the last step)
      - foreach:  {"foreach": {"items": "{{ids}}", "as": "id", "steps": [...], "join": "\\n"}}
                  a for-loop: run the nested `steps` (same shapes as above,
                  nestable) once per item. `items` is a JSON array, one item
                  per line, or one comma-separated line — so a prior step's
                  output usually works as-is. Each iteration sets {{id}}
                  (named by "as"; default {{item}}), {{loop_index}} (1-based)
                  and {{loop_total}}. The step's output is each iteration's
                  last output joined with `join` (default: one per line).
                  A `stop` inside the loop ends the WHOLE workflow; to skip
                  one item use "when" on the body steps. Max 100 items.

    ANY step may also have "when": "<condition>" — it runs only if the condition
    passes (otherwise it's skipped and its variable is ""). Conditions are
    deterministic (no LLM): X == Y, X != Y, X contains Y, X not contains Y,
    X is empty, X is not empty, X > Y, X < Y. Example:
      {"tool": "imessage__...", "when": "{{is_urgent}} == true"}

    Optionally add "triggers": ["turn on movie mode", ...] — short phrases the
    user might say that should run this workflow. If omitted, ~5 are
    auto-generated. They power semantic matching so future requests
    automatically surface this workflow.

    Reference values with {{name}}: params, prior step outputs (by their "id",
    or "step1"/"step2"/...), and built-ins: today, yesterday, tomorrow, now,
    time, weekday. `output` is optional (defaults to the last step's output).
    """
    try:
        defn = json.loads(definition)
    except json.JSONDecodeError as e:
        return f"[ERROR] definition is not valid JSON: {e}"
    try:
        action = store.upsert_workflow(defn)
    except ValueError as e:
        return f"[ERROR] invalid workflow: {e}"
    return f"Workflow '{defn['name']}' {action} ({len(defn.get('steps', []))} steps)."


@mcp.tool()
def list_workflows() -> str:
    """List all saved workflows with description, params (* = required, pass via
    run_workflow's params JSON), step count, and surfaces."""
    workflows = store.load_workflows()
    if not workflows:
        return "No workflows saved yet."
    lines = []
    for w in workflows:
        flags = [k for k, v in (w.get("surfaces") or {}).items() if v]
        pnames = ", ".join(
            p.get("name", "?") + ("*" if p.get("required") else "")
            for p in (w.get("params") or [])
        ) or "none"
        line = (f"- {w['name']}: {w.get('description', '')}\n"
                f"    params: {pnames}  ·  steps: {len(w.get('steps', []))}")
        if flags:
            line += f"  ·  {', '.join(flags)}"
        lines.append(line)
    return "\n".join(lines + ["", "(* = required — pass values via run_workflow's params JSON object)"])


@mcp.tool()
def get_workflow(name: str) -> str:
    """Return the full JSON definition of one workflow."""
    w = store.get_workflow(name)
    if not w:
        return f"No workflow named '{name}'."
    return json.dumps(w, indent=2)


@mcp.tool()
def delete_workflow(name: str) -> str:
    """Delete a workflow by name."""
    if store.delete_workflow(name):
        return f"Deleted workflow '{name}'."
    return f"No workflow named '{name}'."


@mcp.tool()
async def run_workflow(workflow_name: str, params: str = "{}") -> str:
    """
    Run a workflow by name and return ONLY its final output.

    IMPORTANT: most workflows declare params, and required ones (marked * in
    list_workflows) MUST be passed or the run fails. Look up the workflow's
    params first (list_workflows / get_workflow), gather the values, then call
    this with ALL of them in one shot. To run a workflow once per item (e.g.
    one call per session id), either make a separate call per value, or wrap
    it in a `foreach` workflow (see create_workflow) that loops server-side
    and pass the whole list in one call.

    Args:
        workflow_name: the name of the workflow to run (see list_workflows).
        params: JSON object of the workflow's parameter values, e.g.
                '{"session_id": "d5c6fd58-fac3-48b9-b9c3-fa6c815a2f15"}'.
                Only use '{}' (default) when the workflow declares no params.

    Tool steps run deterministically; `prompt` steps run as isolated LLM calls
    that never see this conversation. You get back just the workflow's output.
    """
    try:
        parsed = json.loads(params) if params else {}
    except json.JSONDecodeError as e:
        return f"[ERROR] params is not valid JSON: {e}"
    if not isinstance(parsed, dict):
        return "[ERROR] params must be a JSON object."
    try:
        return await runner.run_workflow(workflow_name, parsed)
    except runner.WorkflowError as e:
        return f"[ERROR] {e}"
    except Exception as e:
        return f"[ERROR] workflow '{workflow_name}' failed: {type(e).__name__}: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
