"""
Flat Agent Core — an experimental, simpler brain, selected per-turn by
config.AGENT_CORE_MODE == "flat". The classic AgentCore (agent/core.py) is left
completely untouched; this is the "other one" you switch to.

How it differs from classic, deliberately:

  - ALL tools are exposed at once (router.get_all_tools) — there are no skills to
    activate; the model sees every tool + definition immediately.
  - NO memories or procedures are injected. The system prompt is a lean identity
    plus the "actions need real tool calls" rule; nothing is retrieved or added.
  - The FULL transcript is kept in the context window and PERSISTED across turns:
    every user/assistant message AND every tool_use / tool_result block. Nothing
    is summarized, threaded, or trimmed, and tool results are kept whole (only a
    very high finite guard). This is meant for a large-context model.
  - No fast-path intent router, no thread lifecycle, no fake-action guard.

It reuses the owning AgentCore's adapter, router, memory (only to mirror clean
text for the dashboard chat view and to honor slash commands), and logging, so it
is a drop-in behind the switch. Its transcript lives in config.FLAT_SESSION_FILE,
isolated from the classic conversation buffer, so flipping modes never corrupts
either one.
"""

import asyncio
import json
import os
from datetime import datetime

import config
from adapters.base import Usage
from agent.interface_prompts import interface_prompt


def flat_system_prompt() -> str:
    """Lean, byte-stable system prompt: identity + the real-tool-calls rule. No
    memory-types blurb, no skill manifest, no procedures — the flat core injects
    none of that."""
    return (
        "You are Second Brain, a general-purpose AI assistant with tool access.\n"
        "Every tool you have is available to you right now — call them directly; "
        "there are no skills to activate.\n\n"
        "## Actions require tool calls — never fake them\n"
        "You can only affect the real world (lights, music, TV, calendar, files, "
        "anything) through tool calls. NEVER say an action is done unless you "
        "actually called the tool for it in THIS turn and saw its result. If no "
        "suitable tool exists or a call fails, say so plainly — never pretend.\n\n"
        "The current date and time are in the [Turn context] line of the latest "
        "user message. Keep replies direct and useful."
    )


class FlatCore:
    """The flat turn engine. One instance per AgentCore, built lazily the first
    time a turn runs in flat mode."""

    def __init__(self, owner):
        self.owner = owner                      # AgentCore: adapter, router, memory, logging
        self._messages: list[dict] | None = None  # persisted transcript (lazy-loaded)
        self._clear_requested = False

    # ---- transcript persistence -------------------------------------------
    @property
    def messages(self) -> list[dict]:
        if self._messages is None:
            self._messages = self._load()
        return self._messages

    def _load(self) -> list[dict]:
        path = config.FLAT_SESSION_FILE
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        # Wire format is provider-specific (OpenAI vs Anthropic block shapes); if
        # the provider changed since this was written, the stored blocks won't
        # replay cleanly — start fresh rather than send malformed messages.
        if data.get("provider") != config.LLM_PROVIDER:
            return []
        return data.get("messages") or []

    def _save(self):
        path = config.FLAT_SESSION_FILE
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"provider": config.LLM_PROVIDER, "model": config.FLAT_MODEL,
                       "messages": self._messages or []}, f)
        os.replace(tmp, path)  # atomic: a crash mid-write can't corrupt the transcript

    def clear(self):
        self._messages = []
        self._save()

    # ---- tools ------------------------------------------------------------
    def _tools(self):
        o = self.owner
        if not o._enable_tools:
            return None
        real = o.router.get_all_tools()
        if not real:
            return None
        # Only meta-tool in flat mode: clear_chat_history, so the user can reset
        # the growing transcript. No activate_skill — everything is already there.
        clear_meta = [m for m in o.router.get_meta_tools() if m["name"] == "clear_chat_history"]
        return o.adapter.format_tools(clear_meta + real)

    # ---- the turn ---------------------------------------------------------
    async def run_turn(self, user_input: str, images: list[dict] | None = None,
                       source: str = "unknown") -> str:
        o = self.owner
        o.last_thread_event = None  # flat mode has no thread lifecycle

        # Slash commands still work (delegated to the classic handlers; they don't
        # touch flat context).
        if user_input.startswith("/remember "):
            text = user_input[10:].strip()
            return (f"Stored in long-term memory (id: {o.memory.remember(text)})"
                    if text else "Usage: /remember <something to remember>")
        if user_input.strip() == "/stats":
            return o._format_stats()
        if user_input.strip() == "/memories":
            return o._format_memories()

        # Turn context: date/time ONLY (this is orientation, not memory).
        now = datetime.now()
        user_content = (f"[Turn context] {now.strftime('%A, %B %d, %Y at %I:%M %p')}\n\n"
                        f"{user_input}")

        msgs = self.messages
        if images:
            blocks = [o.adapter.format_image_block(img) for img in images]
            blocks.append({"type": "text", "text": user_content})
            msgs.append({"role": "user", "content": blocks})
        else:
            msgs.append({"role": "user", "content": user_content})

        # Mirror clean text into the classic conversation buffer for the dashboard
        # chat view. Flat context never READS this back — no injection.
        o.memory.add_user_message(user_input)

        system_prompt = flat_system_prompt() + interface_prompt(source)
        o._last_system_prompt = system_prompt
        o._last_messages = msgs

        tools = self._tools()
        total_usage = Usage()
        total_tool_calls = 0
        response = None
        self._clear_requested = False
        o._cancelled = False
        o._active_task = asyncio.current_task()
        if os.path.exists(config.CANCEL_SIGNAL_FILE):
            os.remove(config.CANCEL_SIGNAL_FILE)

        cap = config.FLAT_MAX_TOOL_RESULT_CHARS
        try:
            for _ in range(config.FLAT_MAX_TOOL_ROUNDS):
                if o._cancelled:
                    break
                response = await o.adapter.chat(system_prompt, msgs, tools,
                                                model=config.FLAT_MODEL)
                total_usage = total_usage + response.usage
                if not response.tool_calls:
                    break

                # Keep the assistant turn (with its tool_use blocks) in-transcript.
                msgs.append(o.adapter.format_assistant_message(response.raw_message))
                total_tool_calls += len(response.tool_calls)

                tool_results = []
                for tc in response.tool_calls:
                    if o._cancelled:
                        break
                    if tc.name == "clear_chat_history":
                        self._clear_requested = True
                        tool_results.append((tc.id,
                            "Transcript will be cleared after this reply — the next "
                            "message starts fresh."))
                        continue
                    if o.on_tool_call:
                        try:
                            o.on_tool_call(tc.name, tc.arguments)
                        except Exception:
                            pass
                    if isinstance(tc.arguments, dict) and "__parse_error__" in tc.arguments:
                        result = f"[ERROR] Could not parse tool arguments: {tc.arguments['__parse_error__']}"
                    elif tc.name == "workflows__run_workflow":
                        result = await o._run_workflow_inproc(tc.arguments)
                    else:
                        result = await o.router.call_tool(tc.name, tc.arguments)

                    o._log_tool_call(tc.name, tc.arguments, result)
                    # Flat core keeps results whole — the cap is a very high finite
                    # guard, not the classic 5k truncation.
                    if len(result) > cap:
                        result = result[:cap] + "\n[...truncated at flat cap]"
                    tool_results.append((tc.id, result))

                trm = o.adapter.format_tool_results(tool_results)
                if isinstance(trm, list):
                    msgs.extend(trm)
                else:
                    msgs.append(trm)

                if o._cancelled:
                    break

            # Round cap hit while the model still wanted tools: one final call with
            # no tools so it answers from what it gathered.
            if response and response.tool_calls and not o._cancelled:
                print(f"  [flat] Hit max tool rounds ({config.FLAT_MAX_TOOL_ROUNDS}); "
                      "requesting final answer")
                response = await o.adapter.chat(system_prompt, msgs, None,
                                                model=config.FLAT_MODEL)
                total_usage = total_usage + response.usage
        except asyncio.CancelledError:
            o._cancelled = True

        assistant_text = "Cancelled." if o._cancelled else ((response.text if response else "") or "")

        if not o._cancelled:
            o._log_agent_reply(assistant_text)
            # The final textual reply goes into the transcript so it's part of the
            # next turn's context (tool_use/tool_result blocks are already in msgs).
            msgs.append({"role": "assistant", "content": assistant_text})

        self._log_and_bill(total_usage, total_tool_calls, source)

        o.memory.add_assistant_message(assistant_text)
        o.memory.conversation.save_session()

        if self._clear_requested:
            self.clear()
        else:
            self._save()
        return assistant_text

    # ---- logging / billing -------------------------------------------------
    def _log_and_bill(self, total_usage: Usage, total_tool_calls: int, source: str):
        if config.LOG_TOKEN_USAGE:
            if total_usage.cost_usd > 0:
                cache_pct = (100 * total_usage.cached_input_tokens / total_usage.input_tokens
                             if total_usage.input_tokens else 0)
                print(f"  [flat] [tokens] in: {total_usage.input_tokens} "
                      f"(cached: {total_usage.cached_input_tokens}, {cache_pct:.0f}%) "
                      f"| out: {total_usage.output_tokens} | cost: ${total_usage.cost_usd:.4f} "
                      f"| msgs: {len(self._messages or [])}")
            else:
                print(f"  [flat] [tokens] in: {total_usage.input_tokens} "
                      f"| out: {total_usage.output_tokens} | msgs: {len(self._messages or [])}")
        try:
            import db
            cost = total_usage.cost_usd or db.compute_cost(
                config.FLAT_MODEL, total_usage.input_tokens, total_usage.output_tokens)
            db.log_api_call(
                source=f"{source}:flat",
                model=config.FLAT_MODEL,
                input_tokens=total_usage.input_tokens,
                output_tokens=total_usage.output_tokens,
                cost_usd=cost,
                tool_calls_count=total_tool_calls,
            )
        except Exception as e:
            print(f"  [flat] billing log skipped: {e}")
