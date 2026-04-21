"""
Conversation memory with rolling summarization.

Maintains a buffer of recent messages (working memory) and a structured
rolling summary of older messages. When the buffer exceeds a threshold,
the oldest messages are summarized and merged into the rolling summary.
"""

import json
import os
import anthropic
import config
from keychain import get_secret


def _content_to_text(content) -> str:
    """Extract plain text from a message content field (string or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, dict) and block.get("type") == "image":
                parts.append("[image]")
        return " ".join(parts)
    return str(content)


def estimate_tokens(text) -> int:
    """Rough token estimate: words * multiplier."""
    if not isinstance(text, str):
        text = _content_to_text(text)
    return int(len(text.split()) * config.TOKEN_ESTIMATION_MULTIPLIER)


class ConversationMemory:
    def __init__(self, session_file: str | None = None):
        self.messages: list[dict] = []
        self.rolling_summary: str = ""
        self.total_messages_processed: int = 0
        self._session_file = session_file or config.SESSION_FILE
        self._client = anthropic.Anthropic(api_key=get_secret("anthropic-api-key"))
        self._load_session()

    @property
    def summary_token_estimate(self) -> int:
        return estimate_tokens(self.rolling_summary) if self.rolling_summary else 0

    @property
    def messages_token_estimate(self) -> int:
        return sum(estimate_tokens(_content_to_text(m["content"])) for m in self.messages)

    def add_message(self, role: str, content: str):
        """Add a message and trigger summarization if needed."""
        self.messages.append({"role": role, "content": content})
        self.total_messages_processed += 1

        # Check if we should summarize
        if len(self.messages) > (config.WORKING_MEMORY_MIN_MESSAGES + config.SUMMARIZE_EVERY_N_MESSAGES):
            self._summarize_oldest()

    def _summarize_oldest(self):
        """Summarize the oldest messages beyond the working memory minimum."""
        keep_count = config.WORKING_MEMORY_MIN_MESSAGES
        to_summarize = self.messages[:-keep_count] if keep_count > 0 else self.messages
        keep = self.messages[-keep_count:] if keep_count > 0 else []

        if not to_summarize:
            return

        # Build the summarization prompt
        conversation_text = ""
        for msg in to_summarize:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            text = _content_to_text(msg["content"])
            conversation_text += f"{role_label}: {text}\n\n"

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
                print(f"  [memory] Summarized {len(to_summarize)} messages → {estimate_tokens(self.rolling_summary)} est. tokens")
        except Exception as e:
            print(f"  [memory] Summarization failed: {e}")
            # Fallback: just keep the old summary and drop messages anyway
            # to prevent unbounded growth

        self.messages = keep

    def get_context(self) -> list[dict]:
        """Return the summary + recent messages formatted for the API."""
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

    def save_session(self):
        """Save conversation state to disk."""
        session = {
            "messages": self.messages,
            "rolling_summary": self.rolling_summary,
            "total_messages_processed": self.total_messages_processed,
        }
        os.makedirs(os.path.dirname(self._session_file), exist_ok=True)
        with open(self._session_file, "w") as f:
            json.dump(session, f, indent=2)
        if config.LOG_TOKEN_USAGE:
            print(f"  [session] Saved {len(self.messages)} messages + summary to disk")

    def _load_session(self):
        """Load conversation state from disk if it exists."""
        if not os.path.exists(self._session_file):
            return
        try:
            with open(self._session_file, "r") as f:
                session = json.load(f)
            self.messages = session.get("messages", [])
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
