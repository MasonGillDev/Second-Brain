"""
Agent Core — shared brain for all interfaces (CLI, Telegram, etc.).

Handles the tool-use loop, memory, and LLM communication.
Interfaces just call `agent.process(message)` and get a response.
"""

import asyncio
import json
import os
import re
import sys
import config
from memory.manager import MemoryManager
from memory.conversation import _is_tool_message
from skills.router import ToolRouter
from adapters.base import Usage
from agent.interface_prompts import interface_prompt


# Replies that assert a completed real-world action. Used by the fake-action
# guard: the model sometimes pattern-completes the terse "Done, ..." replies in
# its history instead of calling a tool (observed: "Done, skipped to the next
# song" with zero tool calls — nothing happened).
_ACTION_CLAIM_RE = re.compile(
    r"\b(done|all set|skipped|paused|resumed|queued|scheduled|cancell?ed|"
    r"turn(?:ed)?\s+(?:on|off)|(?:is|are)\s+now\s+(?:on|off|playing|paused|set)|"
    r"i(?:'ve| have)\s+(?:turned|set|played|skipped|paused|resumed|started|stopped|adjusted|dimmed))\b",
    re.IGNORECASE,
)


def _claims_action(text: str) -> bool:
    return bool(_ACTION_CLAIM_RE.search(text or ""))


def _tool_names(tools: list[dict] | None) -> set[str]:
    """Tool names out of either adapter's wire format (OpenAI or Anthropic)."""
    names = set()
    for t in tools or []:
        name = t.get("name") or (t.get("function") or {}).get("name")
        if name:
            names.add(name)
    return names


def _trace_tool_names(msgs: list[dict]) -> set[str]:
    """Tool names actually called in a message trace (either wire format)."""
    names = set()
    for m in msgs:
        for tc in m.get("tool_calls") or []:
            names.add((tc.get("function") or {}).get("name"))
        content = m.get("content")
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    names.add(b.get("name"))
    names.discard(None)
    return names


def _fabricated_tools(text: str, available: set[str], called: set[str]) -> set[str]:
    """
    Tools the reply names but never actually invoked.

    A reasoning model will narrate a call ("workflows__create_workflow {...}")
    into its prose channel instead of emitting it, then report success. Naming a
    tool it did not call is a far sharper signal than _claims_action's verb list,
    which only catches the terse "Done, ..." phrasings and misses "NOW it's
    actually updated". Reads that legitimately precede a claim (get_workflow,
    then a fabricated create_workflow) leave the counter non-zero, so the count
    alone cannot distinguish them.
    """
    if not text:
        return set()
    return {n for n in available - called if re.search(rf"\b{re.escape(n)}\b", text)}


def create_adapter():
    """Factory: create the right adapter based on config."""
    if config.LLM_PROVIDER == "claude":
        from adapters.claude import ClaudeAdapter
        return ClaudeAdapter()
    elif config.LLM_PROVIDER == "openrouter":
        from adapters.openrouter import OpenRouterAdapter
        return OpenRouterAdapter()
    else:
        raise ValueError(f"Unknown provider: {config.LLM_PROVIDER}")


class AgentCore:
    def __init__(self, enable_tools: bool = True, session_file: str | None = None,
                 threads: bool = False, remote_tools: bool = False,
                 router: ToolRouter | None = None):
        """
        Args:
            enable_tools: If False, skip MCP server startup (for lightweight
                          processes like the scheduler that only need LLM + memory).
            session_file: Optional path to conversation session file.
                          Defaults to config.SESSION_FILE.
            remote_tools: If True, don't spawn MCP servers — proxy every tool
                          call to the dashboard's single running set via its
                          toolbus API (see skills/remote_router.py). Used by
                          telegram and the scheduler so exactly one instance of
                          each server exists machine-wide.
            router:       Borrow an ALREADY-RUNNING router instead of creating
                          one (used by the trigger engine, which lives in the
                          dashboard process next to its router). A borrowed
                          router is never started or shut down by this core.
        """
        self.memory = MemoryManager(session_file=session_file, threads=threads)
        # Thread lifecycle event of the current turn ({"event": "resumed"|"new",
        # "title": ...} or None) — surfaced to interfaces via /api/inference.
        self.last_thread_event: dict | None = None
        self._owns_router = router is None
        if router is not None:
            self.router = router
        elif remote_tools:
            from skills.remote_router import RemoteToolRouter
            self.router = RemoteToolRouter()
        else:
            self.router = ToolRouter()
        self.adapter = create_adapter()
        self._enable_tools = enable_tools and config.TOOLS_ENABLED
        # Fast-path intent router: simple commands skip the LLM entirely.
        from agent.intent_router import IntentRouter
        self.intent_router = IntentRouter(self.memory.vector_store, self.router)
        self._started = False
        self._cancelled = False
        # Set by the clear_chat_history meta-tool; the wipe is deferred to the
        # end of the turn so the agent can still confirm in this reply.
        self._clear_history_requested = False
        self._active_task: asyncio.Task | None = None
        self.on_tool_call = None
        # Serializes process(): a backgrounded voice job must not run the tool-use
        # loop concurrently with another caller (dashboard chat, a follow-up voice
        # turn) — they share conversation state, on_tool_call, _active_task, etc.
        self._run_lock = asyncio.Lock()
        # Serializes memory maintenance (summarization/extraction — blocking LLM
        # calls) against turns. It runs between turns so the reply is never
        # delayed by it; a turn arriving mid-maintenance waits here instead of
        # racing the conversation-buffer trim. Lock order is always
        # _run_lock -> _maintenance_lock; the maintenance task takes only the
        # latter, so there is no deadlock.
        self._maintenance_lock = asyncio.Lock()
        self._maintenance_task: asyncio.Task | None = None
        # Lazily-built alternate brain, used only when config.AGENT_CORE_MODE ==
        # "flat" (see agent/flat_core.py). None until the first flat turn.
        self._flat = None

    async def start(self):
        """Start MCP servers. Call once before processing messages."""
        if self._enable_tools and self._owns_router:
            await self.router.start()
        self._started = True

    async def shutdown(self):
        """Stop MCP servers and save session."""
        # Let in-flight background maintenance finish so it can't race the
        # extraction/save below.
        if self._maintenance_task and not self._maintenance_task.done():
            try:
                await self._maintenance_task
            except Exception:
                pass
        if config.AUTO_EXTRACT_MEMORIES:
            self.memory.extract_memories()
        if config.CONSOLIDATE_ON_SHUTDOWN:
            stats = self.memory.consolidate_memories()
            if config.LOG_TOKEN_USAGE:
                if stats.get("clusters_found", 0) > 0:
                    print(f"  [consolidate] Merged {stats['clusters_found']} clusters: {stats['memories_before']} → {stats['memories_after']} memories")
                else:
                    print(f"  [consolidate] No clusters found ({stats.get('memories_before', 0)} memories checked)")
        # Park the live thread (titled + indexed) so it's routable next startup.
        if self.memory.threads is not None:
            try:
                await asyncio.to_thread(self.memory.park_active_thread)
            except Exception as e:
                print(f"  [threads] shutdown park failed: {e}")
        self.memory.conversation.save_session()
        if self._enable_tools and self._owns_router:
            try:
                await self.router.shutdown()
            except (Exception, BaseException):
                pass

    def cancel(self):
        """Cancel the current processing loop and any active subprocesses."""
        self._cancelled = True
        # Signal the code server to kill its subprocess
        os.makedirs(os.path.dirname(config.CANCEL_SIGNAL_FILE), exist_ok=True)
        with open(config.CANCEL_SIGNAL_FILE, "w") as f:
            f.write("cancel")
        if self._active_task and not self._active_task.done():
            self._active_task.cancel()
        print("  [cancel] Cancellation requested")

    def _build_tools(self) -> list[dict] | None:
        """Every discovered tool, exposed at once — no skill gating. The model
        sees each tool's full schema up front instead of planning against a
        one-line manifest and activating skills mid-turn. Only meta-tool is
        clear_chat_history."""
        if not self._enable_tools:
            return None
        real = self.router.get_all_tools()
        if not real:
            return None
        meta = [m for m in self.router.get_meta_tools()
                if m["name"] == "clear_chat_history"]
        return self.adapter.format_tools(meta + real)

    def is_busy(self) -> bool:
        """True while a process() call is in flight. The voice endpoint uses this
        to reject an overlapping request with a 'still working' ack instead of
        corrupting shared state by running the loop twice at once."""
        return self._run_lock.locked()

    async def _run_workflow_inproc(self, arguments) -> str:
        """Execute a saved workflow using this agent's already-running MCP servers
        (via a RouterBroker) — no duplicate child servers are spawned. `prompt`
        steps still run as isolated LLM calls; only the workflow's final output is
        returned to the model. A hard timeout guarantees a workflow can never hang
        the agent indefinitely."""
        import json as _json
        import workflow_runner
        args = arguments if isinstance(arguments, dict) else {}
        # Tolerate the model's param-name variations: it often sends
        # "workflow_name" instead of "name", and "parameters"/"args" for params.
        name = args.get("name") or args.get("workflow_name") or args.get("workflow")
        raw = args.get("params")
        if raw is None:
            raw = args.get("parameters") or args.get("args") or "{}"
        if isinstance(raw, str):
            try:
                params = _json.loads(raw) if raw.strip() else {}
            except _json.JSONDecodeError:
                params = {}
        else:
            params = raw or {}
        # The model often passes workflow params as extra top-level arguments
        # (run_workflow(workflow_name=..., session_id=...)) instead of nesting
        # them in `params` — harvest any unrecognized keys as params.
        known = {"name", "workflow_name", "workflow", "params", "parameters", "args"}
        for k, v in args.items():
            if k not in known:
                params.setdefault(k, v)
        broker = workflow_runner.RouterBroker(self.router)
        try:
            return await asyncio.wait_for(
                workflow_runner.run_workflow(name, params, broker=broker),
                timeout=180,
            )
        except asyncio.TimeoutError:
            return f"[ERROR] workflow '{name}' timed out after 180s"
        except workflow_runner.WorkflowError as e:
            return f"[ERROR] {e}"
        except Exception as e:
            return f"[ERROR] workflow '{name}' failed: {type(e).__name__}: {e}"

    def _seal_tool_pairs(self, msgs: list[dict]) -> list[dict]:
        """Every tool call in a persisted trace must have a result — a cancel
        can interrupt mid-execution, and replaying an unanswered tool_use is an
        API error on the next turn. Synthesize results for any orphans. Handles
        both wire formats (OpenAI tool_calls/role-tool, Anthropic blocks)."""
        pending: list[str] = []
        answered: set[str] = set()
        for m in msgs:
            for tc in m.get("tool_calls") or []:
                pending.append(tc.get("id"))
            if m.get("role") == "tool":
                answered.add(m.get("tool_call_id"))
            content = m.get("content")
            if isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use":
                        pending.append(b.get("id"))
                    elif b.get("type") == "tool_result":
                        answered.add(b.get("tool_use_id"))
        orphans = [i for i in pending if i and i not in answered]
        if not orphans:
            return msgs
        synthetic = self.adapter.format_tool_results(
            [(i, "[cancelled before execution]") for i in orphans])
        return msgs + (synthetic if isinstance(synthetic, list) else [synthetic])

    @staticmethod
    def _strip_guard_nudges(msgs: list[dict]) -> list[dict]:
        """Drop [SYSTEM CHECK] nudges and the fake-claim assistant replies they
        corrected — steering hacks, not history worth replaying to the model."""
        cleaned: list[dict] = []
        for m in msgs:
            content = m.get("content")
            if (m.get("role") == "user" and isinstance(content, str)
                    and content.startswith("[SYSTEM CHECK]")):
                if cleaned and cleaned[-1].get("role") == "assistant" \
                        and not _is_tool_message(cleaned[-1]):
                    cleaned.pop()
                continue
            cleaned.append(m)
        return cleaned

    async def _try_fast_path(self, user_input: str, source: str) -> str | None:
        """Resolve a simple command to a direct tool call, skipping the LLM.

        Returns a short spoken confirmation on a confident match, or None to let
        the normal LLM pipeline handle it. Fires on_tool_call (so the voice
        endpoint's music_touched tracking still works). Deliberately does NOT
        touch conversation memory — simple commands ("pause the music") would
        pollute topic threads; the Activity Log below is their only record.
        Never raises — any failure falls through to the LLM.
        """
        try:
            resolved = await asyncio.to_thread(self.intent_router.resolve, user_input)
        except Exception as e:
            print(f"  [intent] resolve error, using LLM: {e}")
            return None
        if resolved is None:
            return None

        intent, args = resolved.intent, resolved.args
        print(f"  [intent] {intent.id} @ {resolved.relevance} -> {intent.tool}({args})")

        if self.on_tool_call:
            try:
                self.on_tool_call(intent.tool, args)
            except Exception:
                pass

        try:
            result = await self.router.call_tool(intent.tool, args)
        except Exception as e:
            result = f"[ERROR] {e}"

        reply = intent.confirmation(args, result)

        try:
            import db
            db.log_message("info", "intent",
                           f"{intent.id} @ {resolved.relevance} -> {intent.tool}",
                           details=f"args={args}\nresult={result[:500]}")
        except Exception:
            pass

        return reply

    async def process(self, user_input: str, images: list[dict] | None = None,
                      source: str = "unknown") -> str:
        """Public entry point. Serializes all processing on this agent so a
        backgrounded voice job can't run concurrently with another caller. Quick
        turns acquire and release the lock in milliseconds."""
        async with self._run_lock:
            # If between-turns memory maintenance is mid-flight, wait for it —
            # it mutates the conversation buffer this turn is about to read.
            async with self._maintenance_lock:
                # Runtime switch: the flat core is a separate, simpler brain
                # (all tools at once, no injected memory, full persisted
                # transcript). Read the mode fresh so it can be flipped live from
                # the dashboard config editor without a restart.
                config.reload_overrides()
                if getattr(config, "AGENT_CORE_MODE", "classic") == "flat":
                    return await self._flat_core().run_turn(
                        user_input, images=images, source=source)
                return await self._process_impl(user_input, images=images, source=source)

    def _flat_core(self):
        """Lazily build the flat brain (shares this agent's adapter/router/memory)."""
        if self._flat is None:
            from agent.flat_core import FlatCore
            self._flat = FlatCore(self)
        return self._flat

    def _schedule_memory_maintenance(self):
        """Kick off pending summarization/extraction in the background so the
        reply is never delayed by them. Runs after process() releases the
        maintenance lock; if a run is already in flight, the next turn's check
        picks up whatever is still due."""
        if not self.memory.maintenance_due():
            return
        if self._maintenance_task and not self._maintenance_task.done():
            return

        async def _run():
            async with self._maintenance_lock:
                try:
                    await asyncio.to_thread(self.memory.run_deferred_maintenance)
                except Exception as e:
                    print(f"  [maintenance] Deferred memory maintenance failed: {e}")

        self._maintenance_task = asyncio.create_task(_run())

    async def _process_impl(self, user_input: str, images: list[dict] | None = None,
                            source: str = "unknown") -> str:
        """
        Process a user message and return the agent's response.
        Handles memory, tool routing, and the multi-round tool-use loop.

        Args:
            user_input: The user's text message.
            images: Optional list of image dicts with keys:
                    - "data": base64-encoded image data
                    - "media_type": e.g. "image/png", "image/jpeg"
            source: Where this request came from (dashboard, telegram, scheduler, cli).
        """
        # Reload config overrides (picks up dashboard changes without restart)
        config.reload_overrides()

        # Handle /remember command from any interface
        if user_input.startswith("/remember "):
            text = user_input[10:].strip()
            if text:
                doc_id = self.memory.remember(text)
                return f"Stored in long-term memory (id: {doc_id})"
            return "Usage: /remember <something to remember>"

        if user_input.strip() == "/stats":
            return self._format_stats()

        if user_input.strip() == "/memories":
            return self._format_memories()

        # ── Fast path: simple commands skip the LLM entirely ──
        # Match the transcript to a known intent by embedding similarity and call
        # the tool directly. Text-only (images always go to the LLM), and the
        # router abstains on anything it isn't confident about. Runs before the
        # thread hook: fast-path turns never touch thread state.
        self.last_thread_event = None
        if self._enable_tools and images is None:
            fast = await self._try_fast_path(user_input, source)
            if fast is not None:
                return fast

        # ── Thread lifecycle: park a stale thread, route, resume or start new ──
        # (No-op when threading is off; blocking Haiku/Chroma work off-loop.)
        self.last_thread_event = await asyncio.to_thread(self.memory.begin_turn, user_input)

        # Store images for this request (used when building messages)
        self._pending_images = images

        # Add user message to conversation memory
        self.memory.add_user_message(user_input)

        # Reset cancellation state and register this task so cancel() can interrupt it
        self._cancelled = False
        self._clear_history_requested = False
        self._active_task = asyncio.current_task()
        if os.path.exists(config.CANCEL_SIGNAL_FILE):
            os.remove(config.CANCEL_SIGNAL_FILE)

        # Build context
        system_prompt, messages = self.memory.build_messages(user_input)
        original_msg_count = len(messages)

        # Adapt response style to the calling interface (voice, dashboard, ...).
        # This stays in the system prompt (strong style adherence) even though it
        # varies by source: within one interface it's byte-stable, so the prompt
        # cache only busts when you switch interfaces — rare and bounded.
        system_prompt += interface_prompt(source)

        self._last_system_prompt = system_prompt
        self._last_messages = messages

        # Inject images into the last user message if present
        if self._pending_images:
            for msg in reversed(messages):
                if msg["role"] == "user" and isinstance(msg["content"], str):
                    content_blocks = [
                        self.adapter.format_image_block(img)
                        for img in self._pending_images
                    ]
                    content_blocks.append({"type": "text", "text": msg["content"]})
                    msg["content"] = content_blocks
                    break
            self._pending_images = None

        # Build the tool set (everything, all at once — no skill gating)
        tools = self._build_tools()

        # Tool-use loop
        total_usage = Usage()
        total_tool_calls = 0
        response = None
        nudged = False
        known_tools = _tool_names(tools)
        called_tools: set[str] = set()
        # Tools called in PRIOR turns, visible in the persisted trace. Naming
        # one of these is the model describing history ("I used calendar__get_day
        # yesterday"), not narrating a fake call — the guard must not nudge it
        # into a redundant re-run.
        historic_tools = _trace_tool_names(messages[:original_msg_count])

        try:
            for round_num in range(config.MAX_TOOL_ROUNDS):
                if self._cancelled:
                    break

                response = await self.adapter.chat(system_prompt, messages, tools)
                total_usage = total_usage + response.usage

                if not response.tool_calls:
                    # Fake-action guard: the reply claims something was done,
                    # but no tool ran this turn — nothing actually happened.
                    # Nudge once to act for real (or come clean).
                    #
                    # Two independent tells. A bare action claim only counts
                    # before any tool has run, otherwise every honest summary of
                    # a completed call would trip it. Naming a tool that never
                    # ran is damning at any point in the loop: a real read
                    # followed by a narrated write is the common failure.
                    faked = _fabricated_tools(response.text, known_tools,
                                              called_tools | historic_tools)
                    if tools and not nudged and (
                            faked or (total_tool_calls == 0 and _claims_action(response.text))):
                        nudged = True
                        why = f"named {', '.join(sorted(faked))} without calling it" if faked \
                            else "claimed an action but called no tool"
                        print(f"  [guard] reply {why} — nudging model to act")

                        messages.append({"role": "assistant", "content": response.text})
                        messages.append({"role": "user", "content": (
                            "[SYSTEM CHECK] Your reply claims an action was performed, but you "
                            "did not call any tool this turn — nothing actually happened. "
                            "Call the correct tool(s) now to actually do it, then answer. "
                            "If you cannot do it, say so honestly instead.")})
                        continue
                    break

                # Append assistant message with tool_use blocks
                messages.append(self.adapter.format_assistant_message(response.raw_message))
                called_tools.update(tc.name for tc in response.tool_calls)

                # Execute tools
                tool_results = []

                total_tool_calls += len(response.tool_calls)

                for tc in response.tool_calls:
                    if self._cancelled:
                        break
                    # Handle clear_chat_history meta-tool locally. The actual wipe
                    # is deferred to the end of this turn (see below) so the agent
                    # can still confirm in its reply before the slate is wiped.
                    if tc.name == "clear_chat_history":
                        self._clear_history_requested = True
                        tool_results.append((tc.id,
                            "Chat history will be cleared after this reply — the next "
                            "message starts fresh. Long-term memories are unaffected."))
                        if config.LOG_TOKEN_USAGE:
                            print("  [chat] clear_chat_history requested")
                        continue

                    if self.on_tool_call:
                        self.on_tool_call(tc.name, tc.arguments)

                    if isinstance(tc.arguments, dict) and "__parse_error__" in tc.arguments:
                        result = f"[ERROR] Could not parse tool arguments: {tc.arguments['__parse_error__']}"
                    elif tc.name == "workflows__run_workflow":
                        # Run workflows in-process against THIS agent's already-running
                        # MCP servers. Letting the workflows server spawn its own child
                        # servers can deadlock on shared resources (e.g. the Cync token
                        # lock) and hang the tool call — and thus the whole agent.
                        result = await self._run_workflow_inproc(tc.arguments)
                    else:
                        result = await self.router.call_tool(tc.name, tc.arguments)

                    # Persist the full call + result to the Activity Log (expandable),
                    # before truncating the copy that goes back to the model.
                    self._log_tool_call(tc.name, tc.arguments, result)

                    if len(result) > 5000:
                        result = result[:5000] + "\n[...truncated]"

                    tool_results.append((tc.id, result))

                tool_result_msg = self.adapter.format_tool_results(tool_results)
                if isinstance(tool_result_msg, list):
                    messages.extend(tool_result_msg)
                else:
                    messages.append(tool_result_msg)

                if self._cancelled:
                    break

            # Hit the round cap while the agent still wanted to call tools:
            # make one final call WITHOUT tools so it answers from the results
            # gathered so far, instead of returning the empty/partial text that
            # accompanied the last tool call.
            if response and response.tool_calls and not self._cancelled:
                print(f"  [warning] Hit max tool rounds ({config.MAX_TOOL_ROUNDS}); requesting final answer")
                response = await self.adapter.chat(system_prompt, messages, None)
                total_usage = total_usage + response.usage
        except asyncio.CancelledError:
            # cancel() called _active_task.cancel(); treat as a clean cancellation
            self._cancelled = True

        if self._cancelled:
            assistant_text = "Cancelled."
        else:
            assistant_text = (response.text if response else "") or ""

        # Persist the full agent reply to the Activity Log (expandable)
        if not self._cancelled:
            self._log_agent_reply(assistant_text)

        # Log token usage
        if config.LOG_TOKEN_USAGE:
            if total_usage.cost_usd > 0:
                cache_pct = (100 * total_usage.cached_input_tokens / total_usage.input_tokens
                             if total_usage.input_tokens else 0)
                print(f"  [tokens] in: {total_usage.input_tokens} "
                      f"(cached: {total_usage.cached_input_tokens}, {cache_pct:.0f}%) "
                      f"| out: {total_usage.output_tokens} | cost: ${total_usage.cost_usd:.4f}")
            else:
                input_cost = (total_usage.input_tokens / 1000) * config.INPUT_COST_PER_1K
                output_cost = (total_usage.output_tokens / 1000) * config.OUTPUT_COST_PER_1K
                print(f"  [tokens] in: {total_usage.input_tokens} | out: {total_usage.output_tokens} | cost: ${input_cost + output_cost:.4f}")

        # Persist cost to database
        import db
        # Prefer the provider-reported cost (reflects prompt-cache discounts);
        # fall back to the static per-token estimate when it's absent.
        cost = total_usage.cost_usd or db.compute_cost(
            config.MODEL, total_usage.input_tokens, total_usage.output_tokens)
        db.log_api_call(
            source=source,
            model=config.MODEL,
            input_tokens=total_usage.input_tokens,
            output_tokens=total_usage.output_tokens,
            cost_usd=cost,
            tool_calls_count=total_tool_calls,
        )

        # Persist this turn's NATIVE tool trace (assistant tool_use messages +
        # tool results, in the provider's wire format) so the model keeps its
        # own actions in context on later turns instead of only its prose. As
        # real API blocks these don't trigger imitation the way text-rendered
        # "[Tool calls] ..." traces did — the model just sees authentic history.
        # Guard nudges are stripped and orphaned tool calls sealed (cancel can
        # interrupt mid-execution) so the trace always replays cleanly.
        turn_trace = self._strip_guard_nudges(messages[original_msg_count:])
        turn_trace = self._seal_tool_pairs(turn_trace)
        if turn_trace:
            self.memory.conversation.add_native_messages(turn_trace)

        # The clean final reply follows the trace as a plain assistant message.
        self.memory.add_assistant_message(assistant_text)
        self.memory.conversation.save_session()

        # Deferred clear: the agent asked to wipe the conversation this turn. Do it
        # now (after the reply is built + saved) so this turn's confirmation is what
        # the user sees, but the next turn starts with an empty history. Under
        # threading this is a cold start: the thread is parked (kept + resumable),
        # never deleted.
        if self._clear_history_requested:
            await asyncio.to_thread(self.memory.cold_start)
            self._clear_history_requested = False
            if config.LOG_TOKEN_USAGE:
                print("  [chat] Chat history cleared")

        # Summarization/extraction used to run inline above (inside add_*_message),
        # adding a full blocking Haiku round trip to the reply on the turns where
        # they triggered. They now run in the background between turns.
        self._schedule_memory_maintenance()

        return assistant_text

    @staticmethod
    def _cap(text: str) -> str:
        """Cap a log detail blob at LOG_DETAIL_MAX_BYTES, marking truncation."""
        cap = config.LOG_DETAIL_MAX_BYTES
        if len(text) <= cap:
            return text
        return text[:cap] + f"\n[...truncated at {cap // 1024} KB]"

    def _log_tool_call(self, name: str, arguments, result: str):
        """Persist a full tool call + result as one expandable Activity Log entry."""
        if not config.LOG_TOKEN_USAGE:
            return
        try:
            args_str = (json.dumps(arguments, indent=2, default=str)
                        if isinstance(arguments, (dict, list)) else str(arguments))
        except Exception:
            args_str = str(arguments)
        preview = " ".join(args_str.split())[:80]
        summary = f"{name}({preview})"
        details = (f"▼ Arguments\n{self._cap(args_str)}\n\n"
                   f"▼ Result ({len(result):,} chars)\n{self._cap(result)}")
        try:
            sys.__stdout__.write(f"  [tool] {summary}\n")  # console echo, not re-captured to DB
        except Exception:
            pass
        try:
            import db
            db.log_message("info", "tool", summary, details=details)
        except Exception:
            pass

    def _log_agent_reply(self, text: str):
        """Persist the full agent reply as an expandable Activity Log entry."""
        if not config.LOG_TOKEN_USAGE or not text:
            return
        preview = " ".join(text.split())[:80]
        details = self._cap(text) if (len(text.strip()) > 80 or "\n" in text) else None
        try:
            import db
            db.log_message("info", "agent", preview, details=details)
        except Exception:
            pass

    @staticmethod
    def _tool_messages_to_text(tool_messages: list[dict]) -> str:
        """Convert tool loop messages to plain text, handling any content format."""
        lines = []
        for msg in tool_messages:
            content = msg.get("content")
            if content is None:
                continue
            # String content — just include it
            if isinstance(content, str):
                if content.strip():
                    lines.append(content.strip())
                continue
            # List of blocks
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, str):
                        if block.strip():
                            lines.append(block.strip())
                    elif isinstance(block, dict):
                        text = block.get("text") or block.get("content") or ""
                        name = block.get("name", "")
                        inp = block.get("input")
                        if name and inp is not None:
                            args = json.dumps(inp)
                            if len(args) > 300:
                                args = args[:300] + "..."
                            lines.append(f"Called: {name}({args})")
                        if isinstance(text, str) and text.strip():
                            t = text.strip()
                            if len(t) > 1000:
                                t = t[:1000] + "..."
                            lines.append(t)
                    else:
                        s = str(block).strip()
                        if s:
                            lines.append(s)
                continue
            # Fallback
            s = str(content).strip()
            if s:
                lines.append(s)
        return "\n".join(lines)

    def _format_stats(self) -> str:
        stats = self.memory.get_stats()
        lines = ["Memory Statistics:"]
        lines.append(f"  Conversation: {stats['conversation']['recent_messages']} recent messages, {stats['conversation']['total_processed']} total")
        lines.append(f"  Summary: ~{stats['conversation']['summary_tokens_est']} tokens")
        for name, count in stats['vector_store'].items():
            lines.append(f"  {name}: {count} entries")
        return "\n".join(lines)

    def _format_memories(self) -> str:
        """Dump all long-term memories directly from ChromaDB."""
        collection = self.memory.vector_store.collections["long_term"]
        if collection.count() == 0:
            return "No long-term memories stored."

        results = collection.get(limit=50)
        lines = [f"Long-Term Memories ({collection.count()} total):\n"]
        for doc_id, text, meta in zip(
            results["ids"], results["documents"], results["metadatas"]
        ):
            category = meta.get("category", meta.get("type", ""))
            access_count = meta.get("access_count", 0)
            lines.append(f"  [{doc_id}] ({category}) x{access_count} — {text}")
        return "\n".join(lines)
