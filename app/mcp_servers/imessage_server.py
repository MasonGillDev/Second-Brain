"""
iMessage MCP Server.

Read-only access to iMessage history. All database work lives in
app/imessage_store.py; this file only maps it to tools and phrases results.

Requires Full Disk Access for the running process.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from imessage_store import (
    MessageError,
    conversations as _conversations,
    recent_messages as _recent,
    search as _search,
    send_message as _send,
    unread as _unread,
)
from reply_watch import (
    cancel as _cancel_watch,
    pending as _pending_watches,
    send_and_watch as _send_and_watch,
)

mcp = FastMCP("imessage")


def _render(messages: list[dict], show_chat: bool = False) -> str:
    lines = []
    for m in messages:
        prefix = f"[{m['date']}] "
        if show_chat and m.get("chat"):
            prefix += f"({m['chat']}) "
        flag = " [unread]" if m["unread"] else ""
        lines.append(f"{prefix}{m['sender']}: {m['text']}{flag}")
    return "\n".join(lines)


def _also_matched(others: list[str]) -> str:
    """Name resolution is ambiguous by nature — say who else matched."""
    return f"\n\n(Also matched: {', '.join(others)}. Ask for one by name to see theirs.)" if others else ""


@mcp.tool()
def get_recent_messages(contact: str = "", count: int = 20,
                        include_groups: bool = False) -> str:
    """
    Get the most recent messages, optionally with one contact.

    Shows both sides of the conversation — yours and theirs.

    Args:
        contact: Who to read. A contact NAME as it appears in Contacts ("Char",
                 "Mom"), or a phone number or email. Names are matched against
                 Contacts, so partial names work; if several people match, the one
                 you've messaged most recently wins and the rest are listed.
                 Leave empty for recent messages across all conversations.
        count: How many messages to return (default 20, max 100).
        include_groups: Also include group threads this person is in. Off by
                        default so a name gives you the one-on-one conversation.
    """
    count = min(max(count, 1), 100)
    try:
        result = _recent(contact, count, include_groups)
    except MessageError as e:
        return f"[ERROR] {e}"

    if not result["messages"]:
        return f"No messages found{' with ' + contact if contact else ''}."

    who = f" with {result['name']}" if result["name"] else ""
    header = f"Last {len(result['messages'])} messages{who}:\n"
    return header + _render(result["messages"], show_chat=include_groups) + _also_matched(result["others"])


@mcp.tool()
def search_messages(query: str, contact: str = "", count: int = 20) -> str:
    """
    Search message history for a keyword.

    Args:
        query: Text to look for.
        contact: Optional contact name, phone number or email to narrow the search.
        count: Max results (default 20, max 100).
    """
    count = min(max(count, 1), 100)
    try:
        result = _search(query, contact, count)
    except MessageError as e:
        return f"[ERROR] {e}"

    if not result["messages"]:
        who = f" with {result['name'] or contact}" if contact else ""
        return f"No messages matching '{query}'{who}."

    who = f" with {result['name']}" if result["name"] else ""
    header = f"{len(result['messages'])} matches for '{query}'{who}:\n"
    return header + _render(result["messages"], show_chat=True) + _also_matched(result["others"])


@mcp.tool()
def get_unread_messages() -> str:
    """Get unread incoming messages across all conversations."""
    try:
        messages = _unread()
    except MessageError as e:
        return f"[ERROR] {e}"
    if not messages:
        return "No unread messages."
    return f"{len(messages)} unread:\n" + _render(messages, show_chat=True)


@mcp.tool()
def list_conversations(count: int = 20) -> str:
    """
    List the most recently active conversations, newest first.

    Use this to see who has been texting, or to find the exact contact name to
    pass to get_recent_messages.

    Args:
        count: How many threads to list (default 20, max 100).
    """
    count = min(max(count, 1), 100)
    try:
        threads = _conversations(count)
    except MessageError as e:
        return f"[ERROR] {e}"
    if not threads:
        return "No conversations found."
    return "\n".join(
        f"{t['name']} — {t['date']}"
        + (f" [{t['unread']} unread]" if t["unread"] else "")
        + (" (group)" if t["group"] else "")
        for t in threads
    )


@mcp.tool()
def send_message(to: str, text: str, confirm: bool = False,
                 await_reply: bool = False, reply_intent: str = "") -> str:
    """
    Send an iMessage. Two steps: call once to preview, again to actually send.

    Contact names are fuzzy — several people can match one name — and a text sent
    to the wrong person cannot be recalled. So the first call ALWAYS returns a
    preview showing exactly who it resolved to, and sends nothing. Show that
    preview to the user, get their agreement, then call again with confirm=true.

    Never pass confirm=true on the first call, and never pass it without the user
    having seen the resolved recipient.

    Args:
        to: Who to text. A contact NAME as in Contacts ("Char", "Mom"), or a phone
            number or email.
        text: The message body, exactly as it should be sent.
        confirm: False previews. True sends, and is only appropriate after the
                 user has seen and approved a preview.
        await_reply: Keep watching the conversation after sending, and wake up
                 when they answer. Use this whenever the message ASKS something
                 whose answer you need to act on. The wait survives restarts and
                 lasts up to a day, so it is fine if they take hours.
        reply_intent: Required with await_reply — what to DO once they answer,
                 written as an instruction to your future self, because you will
                 have no memory of this conversation when it fires. Name the
                 specific record to change, e.g. "update tonight's 7pm calendar
                 event 'Dinner' with the restaurant she names".
    """
    if await_reply and not reply_intent.strip():
        return ("[ERROR] await_reply needs reply_intent — say what to do once they "
                "answer (e.g. \"update tonight's Dinner event with the location\").")
    try:
        if await_reply:
            result = _send_and_watch(to, text, reply_intent, confirm=confirm)
        else:
            result = _send(to, text, confirm=confirm)
    except MessageError as e:
        return f"[ERROR] {e}"

    others = (f"\n\nHeads up — '{to}' also matched: {', '.join(result['others'])}. "
              "Confirm this is the right person before sending."
              ) if result["others"] else ""

    if not result["sent"]:
        follow = f"\n  Then: {reply_intent}" if await_reply else ""
        return (
            "DRY RUN — nothing sent yet.\n"
            f"  To:   {result['name']}  <{result['handle']}>\n"
            f"  Text: {result['text']}{follow}\n"
            "Show this to the user. If they approve, call again with confirm=true."
            + others
        )

    sent = f"Sent to {result['name']} <{result['handle']}> via {result['service']}: {result['text']}"
    watch = result.get("watch")
    if watch:
        sent += (f"\n\nWatching for {result['name']}'s reply (watch #{watch['id']}). "
                 f"When they answer I'll be woken to: {watch['intent']}. "
                 "Tell the user you'll handle it when she replies — do not wait here.")
    return sent


@mcp.tool()
def list_pending_replies() -> str:
    """
    Show questions you texted that are still waiting on an answer.

    Use this when the user asks what you're waiting on, or before texting the
    same person the same question twice.
    """
    import time

    watches = _pending_watches()
    if not watches:
        return "Not waiting on any replies."
    lines = []
    for w in watches:
        waited = (time.time() - w["created_at"]) / 3600
        left = (w["expires_at"] - time.time()) / 3600
        status = "reply landed, settling" if w["first_reply_at"] else "no reply yet"
        lines.append(
            f"#{w['id']} {w['contact_name']} — asked {waited:.1f}h ago, {status}, "
            f"expires in {left:.0f}h\n    Q: {w['question'][:100]}\n    Then: {w['intent'][:100]}")
    return f"Waiting on {len(watches)} reply(ies):\n" + "\n".join(lines)


@mcp.tool()
def cancel_pending_reply(watch_id: int) -> str:
    """
    Stop waiting on a reply. Use when the user answers it another way, or says
    to drop it. Get the id from list_pending_replies.
    """
    return (f"Cancelled watch #{watch_id}." if _cancel_watch(watch_id)
            else f"No pending watch #{watch_id} (already fired, expired, or cancelled).")


if __name__ == "__main__":
    mcp.run(transport="stdio")
