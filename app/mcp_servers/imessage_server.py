"""
iMessage MCP Server.

Read-only access to iMessage history. All database work lives in
app/imessage_store.py; this file only maps it to tools and phrases results.

Requires Full Disk Access for the running process.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server.fastmcp import FastMCP

from app.imessage_store import (
    MessageError,
    conversations as _conversations,
    recent_messages as _recent,
    search as _search,
    unread as _unread,
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
