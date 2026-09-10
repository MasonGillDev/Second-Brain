"""
Conversation memory with rolling summarization.

Maintains a buffer of recent messages (working memory) and a structured
rolling summary of older messages. The buffer holds NATIVE provider-format
messages — including assistant tool_use/tool_calls and their tool results —
so the model sees its own tool activity on later turns instead of waking up
with only its prose replies (the old design's amnesia).

Compaction works on whole TURNS (a real user message plus everything up to
the next one): when the buffer outgrows its token budget, the oldest turns —
tool calls and results rendered inline — are folded into the rolling summary
and the newest turns stay verbatim. A turn is never split, so a tool_use can
never be separated from its tool_result.

The session file is tagged with the provider that wrote it; if the provider
changes, tool-bearing messages (whose wire shapes are provider-specific) are
dropped on load and only plain text survives.
"""

import json
import os
import anthropic
import config
from keychain import get_secret


def _shorten(text: str, limit: int) -> str:
    if limit and len(text) > limit:
        return text[:limit] + "…"
    return text


def _block_result_text(content) -> str:
    """A tool_result block's content may be a plain string or nested blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text")
    return str(content)


def _content_to_text(content) -> str:
    """Extract plain text from a message content field (string or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, dict) and block.get("type") in ("image", "image_url"):
                parts.append("[image]")
        return " ".join(parts)
    return str(content)


def _message_to_text(msg: dict, full: bool = False) -> str:
    """Render ANY buffered message — plain text, assistant tool calls, or tool
    results, in either provider's wire format — to readable text. Used for
    summarization, extraction, token estimation, and thread indexing.

    With full=False, tool arguments and results are truncated to what a
    summary needs; full=True renders everything (honest token estimates).
    """
    arg_cap = 0 if full else 200
    res_cap = 0 if full else 400

    # OpenAI-format tool result: a whole message with role "tool".
    if msg.get("role") == "tool":
        text = _block_result_text(msg.get("content"))
        return f"[tool result: {_shorten(text, res_cap)}]"

    parts = []
    content = msg.get("content")
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            btype = b.get("type")
            if btype == "text":
                parts.append(b.get("text", ""))
            elif btype in ("image", "image_url"):
                parts.append("[image]")
            elif btype == "tool_use":  # Anthropic-format call
                args = json.dumps(b.get("input", {}))
                parts.append(f"[called {b.get('name')}({_shorten(args, arg_cap)})]")
            elif btype == "tool_result":  # Anthropic-format result
                text = _block_result_text(b.get("content"))
                parts.append(f"[tool result: {_shorten(text, res_cap)}]")
    elif content is not None:
        parts.append(str(content))

    for tc in msg.get("tool_calls") or []:  # OpenAI-format calls
        fn = tc.get("function") or {}
        args = fn.get("arguments") or ""
        parts.append(f"[called {fn.get('name')}({_shorten(args, arg_cap)})]")

    return " ".join(p for p in parts if p)


def _is_tool_message(msg: dict) -> bool:
    """True for any message carrying tool machinery in either wire format."""
    if msg.get("role") == "tool" or msg.get("tool_calls"):
        return True
    content = msg.get("content")
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") in ("tool_use", "tool_result")
                   for b in content)
    return False


def _is_turn_start(msg: dict) -> bool:
    """A turn starts at a REAL user message — not a tool result riding in the
    user role (Anthropic format) and not a mid-turn [SYSTEM CHECK] nudge."""
    if msg.get("role") != "user" or _is_tool_message(msg):
        return False
    content = msg.get("content")
    if isinstance(content, str) and content.startswith("[SYSTEM CHECK]"):
        return False
    return True


def _split_turns(messages: list[dict]) -> list[list[dict]]:
    """Partition the buffer into whole turns. Anything before the first real
    user message (legacy leftovers) rides with the first turn."""
    turns: list[list[dict]] = []
    for msg in messages:
        if _is_turn_start(msg) or not turns:
            turns.append([msg])
        else:
            turns[-1].append(msg)
    return turns


def estimate_tokens(text) -> int:
    """Rough token estimate: words * multiplier."""
    if not isinstance(text, str):
        text = _content_to_text(text)
    return int(len(text.split()) * config.TOKEN_ESTIMATION_MULTIPLIER)


def _message_tokens(msg: dict) -> int:
    return estimate_tokens(_message_to_text(msg, full=True))


class ConversationMemory:
    def __init__(self, session_file: str | None = None):
        self.messages: list[dict] = []
        self.rolling_summary: str = ""
        self.total_messages_processed: int = 0
        self._session_file = session_file or config.SESSION_FILE
        # When set (threading enabled), the working-memory budget is derived
        # from this ceiling instead of config.WORKING_MEMORY_TOKEN_BUDGET, so a
        # thread can hold deep verbatim context.
        self.token_ceiling: int | None = None
        self._client = anthropic.Anthropic(api_key=get_secret("anthropic-api-key"))
        self._load_session()

    def to_state(self) -> dict:
        """Snapshot the conversation state (thread park/rehydrate). NOTE: the
        messages are provider-native; a parked thread rehydrated under a
        different LLM_PROVIDER won't replay its tool traces cleanly."""
        return {
            "messages": list(self.messages),
            "rolling_summary": self.rolling_summary,
            "total_messages_processed": self.total_messages_processed,
        }

    def load_state(self, state: dict, session_file: str | None = None):
        """Replace the live buffer with a saved state (thread rehydrate/new).
        Future save_session() calls persist to `session_file` when given."""
        self.messages = list(state.get("messages", []))
        self.rolling_summary = state.get("rolling_summary", "")
        self.total_messages_processed = state.get("total_messages_processed", 0)
        if session_file:
            self._session_file = session_file

    @property
    def summary_token_estimate(self) -> int:
        return estimate_tokens(self.rolling_summary) if self.rolling_summary else 0

    @property
    def messages_token_estimate(self) -> int:
        return sum(_message_tokens(m) for m in self.messages)

    def add_message(self, role: str, content: str):
        """Add a plain text message. Summarization is NOT triggered here — it's
        a blocking LLM call, so the agent defers it to between-turns memory
        maintenance (AgentCore._schedule_memory_maintenance)."""
        self.messages.append({"role": role, "content": content})
        self.total_messages_processed += 1

    def add_native_messages(self, msgs: list[dict]):
        """Append provider-native messages (assistant tool_use/tool_calls and
        their tool results) verbatim, so the model keeps its own tool activity
        in context on later turns."""
        self.messages.extend(msgs)
        self.total_messages_processed += len(msgs)

    def _working_budget(self) -> int:
        """Token budget for the verbatim message buffer."""
        if self.token_ceiling is not None:
            return max(1000, self.token_ceiling - self.summary_token_estimate)
        return config.WORKING_MEMORY_TOKEN_BUDGET

    def needs_summarization(self) -> bool:
        """True when the buffer has outgrown its token budget and old turns
        should be folded into the rolling summary. The newest turns are always
        kept, so with only WORKING_MEMORY_MIN_TURNS turns present there is
        nothing to fold regardless of size."""
        if len(_split_turns(self.messages)) <= config.WORKING_MEMORY_MIN_TURNS:
            return False
        return self.messages_token_estimate > self._working_budget()

    def summarize_oldest(self):
        """Fold the oldest whole turns into the rolling summary, keeping the
        newest WORKING_MEMORY_MIN_TURNS turns unconditionally plus as many more
        as fit the token budget. Folded turns are rendered WITH their tool
        calls and results so concrete outcomes (ids, paths, params, errors)
        survive into the summary instead of vanishing with the trace.
        Blocking (sync LLM call) — run via asyncio.to_thread off the reply path."""
        turns = _split_turns(self.messages)
        if len(turns) <= config.WORKING_MEMORY_MIN_TURNS:
            return

        budget = self._working_budget()
        kept_tokens = 0
        keep_turns = 0
        for turn in reversed(turns):
            turn_tokens = sum(_message_tokens(m) for m in turn)
            if keep_turns < config.WORKING_MEMORY_MIN_TURNS or kept_tokens + turn_tokens <= budget:
                keep_turns += 1
                kept_tokens += turn_tokens
            else:
                break

        to_summarize = [m for turn in turns[:-keep_turns] for m in turn]
        keep = [m for turn in turns[-keep_turns:] for m in turn]
        if not to_summarize:
            return

        role_labels = {"user": "User", "assistant": "Assistant", "tool": "Tool"}
        conversation_text = ""
        for msg in to_summarize:
            label = role_labels.get(msg.get("role"), "Assistant")
            conversation_text += f"{label}: {_message_to_text(msg)}\n\n"

        existing_summary_section = ""
        if self.rolling_summary:
            existing_summary_section = (
                f"\n## Existing Summary\n{self.rolling_summary}\n\n"
                "Integrate the new messages into a new summary. "
                "Update any sections that have changed. Remove information that is no longer relevant. Keep it consise and relevent.\n"
            )

        prompt = f"""Summarize the following conversation messages into a structured summary.{existing_summary_section}

## New Messages to Summarize
{conversation_text}

## Output Format
Use this exact structure:

### Current Goals
- What the user is trying to accomplish right now

### Key Facts Established
- Important information, decisions, or facts from the conversation
- Notable tool actions and their CONCRETE outcomes — keep exact ids, file paths, parameter values, and error messages verbatim

### Decisions Made
- Any choices or conclusions reached

### Open Questions
- Anything unresolved or pending

### Context
- Any other relevant context (user preferences, constraints, etc.)

Be concise but preserve all important details. Use bullet points. Do not include filler."""

        try:
            response = self._client.messages.create(
                model=config.SUMMARIZATION_MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            self.rolling_summary = response.content[0].text

            if config.LOG_TOKEN_USAGE:
                print(f"  [memory] Compacted {len(turns) - keep_turns} turns "
                      f"({len(to_summarize)} messages) → summary ~{estimate_tokens(self.rolling_summary)}t, "
                      f"kept {keep_turns} turns ~{kept_tokens}t")

            import db
            cost = db.compute_cost(config.SUMMARIZATION_MODEL, response.usage.input_tokens, response.usage.output_tokens)
            db.log_api_call("summarization", config.SUMMARIZATION_MODEL,
                            response.usage.input_tokens, response.usage.output_tokens, cost)
        except Exception as e:
            print(f"  [memory] Summarization failed: {e}")
            # Fallback: just keep the old summary and drop messages anyway
            # to prevent unbounded growth

        self.messages = keep

    def get_context(self) -> list[dict]:
        """Return the summary + recent messages formatted for the API. The
        buffer already holds native tool_use/tool_result messages, so recent
        turns replay with full tool context."""
        context = []
        if self.rolling_summary:
            context.append({
                "role": "user",
                "content": f"[CONVERSATION SUMMARY - This summarizes our earlier conversation]\n{self.rolling_summary}"
            })
            context.append({
                "role": "assistant",
                "content": "Understood, I have the context from our earlier conversation."
            })

        context.extend(self.messages)

        return context

    def display_messages(self) -> list[dict]:
        """The buffer rendered for a chat UI: user/assistant text only — tool
        machinery, empty tool-call-only turns, and guard nudges are skipped."""
        out = []
        for m in self.messages:
            if m.get("role") not in ("user", "assistant") or _is_tool_message(m):
                continue
            text = _content_to_text(m.get("content"))
            if not text or text.startswith("[SYSTEM CHECK]"):
                continue
            out.append({"role": m["role"], "content": text})
        return out

    def save_session(self):
        """Save conversation state to disk. Tagged with the provider whose wire
        format the buffered messages use."""
        session = {
            "provider": config.LLM_PROVIDER,
            "messages": self.messages,
            "rolling_summary": self.rolling_summary,
            "total_messages_processed": self.total_messages_processed,
        }
        os.makedirs(os.path.dirname(self._session_file), exist_ok=True)
        tmp = self._session_file + ".tmp"
        with open(tmp, "w") as f:
            json.dump(session, f, indent=2)
        os.replace(tmp, self._session_file)  # atomic: a crash can't corrupt the session
        if config.LOG_TOKEN_USAGE:
            print(f"  [session] Saved {len(self.messages)} messages + summary to disk")

    def _load_session(self):
        """Load conversation state from disk if it exists. If the session was
        written under a different provider, tool-bearing messages (whose wire
        shapes are provider-specific) are dropped and plain text kept."""
        if not os.path.exists(self._session_file):
            return
        try:
            with open(self._session_file, "r") as f:
                session = json.load(f)
            messages = session.get("messages", [])
            stored_provider = session.get("provider")
            if stored_provider and stored_provider != config.LLM_PROVIDER:
                before = len(messages)
                messages = [m for m in messages
                            if m.get("role") in ("user", "assistant")
                            and not _is_tool_message(m)
                            and isinstance(m.get("content"), str)]
                print(f"  [session] Provider changed ({stored_provider} → {config.LLM_PROVIDER}); "
                      f"dropped {before - len(messages)} tool-trace messages")
            self.messages = messages
            self.rolling_summary = session.get("rolling_summary", "")
            self.total_messages_processed = session.get("total_messages_processed", 0)
            if config.LOG_TOKEN_USAGE:
                print(f"  [session] Restored {len(self.messages)} messages + summary from last session")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [session] Failed to load session: {e}")

    def clear_session(self):
        """Wipe conversation state and delete the session file."""
        self.messages = []
        self.rolling_summary = ""
        self.total_messages_processed = 0
        if os.path.exists(self._session_file):
            os.remove(self._session_file)

    def get_stats(self) -> dict:
        return {
            "recent_messages": len(self.messages),
            "total_processed": self.total_messages_processed,
            "summary_tokens_est": self.summary_token_estimate,
            "messages_tokens_est": self.messages_token_estimate,
        }
