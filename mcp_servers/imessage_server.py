"""
iMessage MCP Server.

Read-only access to iMessage history via the local chat.db SQLite database.
Requires Full Disk Access for the Python process in System Settings > Privacy & Security.

Tools:
  - get_recent_messages: Last N messages from a contact or all contacts
  - search_messages: Search message history by keyword
  - get_unread_messages: Get all unread incoming messages
"""

import sys
import os
import sqlite3
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("imessage")

# iMessage database path
CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")

# Apple epoch: 2001-01-01 00:00:00 UTC
# iMessage dates are nanoseconds since this epoch
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def _get_connection() -> sqlite3.Connection:
    """Get a read-only connection to chat.db."""
    if not os.path.exists(CHAT_DB):
        raise FileNotFoundError(f"iMessage database not found at {CHAT_DB}")
    conn = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _apple_date_to_str(apple_date: int | None) -> str:
    """Convert Apple nanosecond timestamp to readable string."""
    if not apple_date:
        return "unknown"
    try:
        # iMessage dates are nanoseconds since 2001-01-01
        seconds = apple_date / 1_000_000_000
        dt = APPLE_EPOCH + timedelta(seconds=seconds)
        return dt.astimezone().strftime("%Y-%m-%d %I:%M %p")
    except (ValueError, OverflowError):
        return "unknown"


def _format_messages(rows) -> str:
    """Format message rows into readable text."""
    if not rows:
        return "No messages found."

    lines = []
    for row in rows:
        direction = "Me" if row["is_from_me"] else (row["contact"] or "Unknown")
        date = _apple_date_to_str(row["date"])
        text = row["text"] or "(attachment)"
        read_status = "" if row["is_from_me"] else (" [unread]" if not row["is_read"] else "")
        lines.append(f"[{date}] {direction}: {text}{read_status}")

    return "\n".join(lines)


@mcp.tool()
def get_recent_messages(contact: str = "", count: int = 20) -> str:
    """
    Get recent messages, optionally filtered by contact.

    Args:
        contact: Phone number or email to filter by (e.g., "+1234567890", "name@email.com").
                 Leave empty to get messages from all contacts.
        count: Number of messages to return (default 20, max 100).
    """
    count = min(max(count, 1), 100)

    try:
        conn = _get_connection()

        if contact:
            rows = conn.execute("""
                SELECT
                    m.text,
                    m.date,
                    m.is_from_me,
                    m.is_read,
                    h.id as contact
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                WHERE h.id LIKE ?
                ORDER BY m.date DESC
                LIMIT ?
            """, (f"%{contact}%", count)).fetchall()
        else:
            rows = conn.execute("""
                SELECT
                    m.text,
                    m.date,
                    m.is_from_me,
                    m.is_read,
                    h.id as contact
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                ORDER BY m.date DESC
                LIMIT ?
            """, (count,)).fetchall()

        conn.close()

        # Reverse so oldest first
        rows = list(reversed(rows))
        header = f"Recent messages{' with ' + contact if contact else ''} ({len(rows)}):\n"
        return header + _format_messages(rows)

    except FileNotFoundError as e:
        return f"[ERROR] {e}"
    except sqlite3.OperationalError as e:
        if "unable to open" in str(e):
            return "[ERROR] Permission denied. Grant Full Disk Access to your terminal/Python in System Settings > Privacy & Security."
        return f"[ERROR] Database error: {e}"
    except Exception as e:
        return f"[ERROR] {e}"


@mcp.tool()
def search_messages(query: str, contact: str = "", count: int = 20) -> str:
    """
    Search message history by keyword.

    Args:
        query: Text to search for in messages.
        contact: Optional phone number or email to narrow the search.
        count: Max results to return (default 20, max 100).
    """
    count = min(max(count, 1), 100)

    try:
        conn = _get_connection()

        if contact:
            rows = conn.execute("""
                SELECT
                    m.text,
                    m.date,
                    m.is_from_me,
                    m.is_read,
                    h.id as contact
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                WHERE m.text LIKE ? AND h.id LIKE ?
                ORDER BY m.date DESC
                LIMIT ?
            """, (f"%{query}%", f"%{contact}%", count)).fetchall()
        else:
            rows = conn.execute("""
                SELECT
                    m.text,
                    m.date,
                    m.is_from_me,
                    m.is_read,
                    h.id as contact
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                WHERE m.text LIKE ?
                ORDER BY m.date DESC
                LIMIT ?
            """, (f"%{query}%", count)).fetchall()

        conn.close()

        rows = list(reversed(rows))
        header = f"Search results for '{query}'{' with ' + contact if contact else ''} ({len(rows)}):\n"
        return header + _format_messages(rows)

    except FileNotFoundError as e:
        return f"[ERROR] {e}"
    except sqlite3.OperationalError as e:
        if "unable to open" in str(e):
            return "[ERROR] Permission denied. Grant Full Disk Access to your terminal/Python in System Settings > Privacy & Security."
        return f"[ERROR] Database error: {e}"
    except Exception as e:
        return f"[ERROR] {e}"


@mcp.tool()
def get_unread_messages() -> str:
    """
    Get all unread incoming messages. Only shows messages from others (not your own sent messages).
    """
    try:
        conn = _get_connection()

        rows = conn.execute("""
            SELECT
                m.text,
                m.date,
                m.is_from_me,
                m.is_read,
                h.id as contact
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.ROWID
            WHERE m.is_read = 0 AND m.is_from_me = 0 AND m.text IS NOT NULL
            ORDER BY m.date DESC
            LIMIT 50
        """).fetchall()

        conn.close()

        rows = list(reversed(rows))

        if not rows:
            return "No unread messages."

        return f"Unread messages ({len(rows)}):\n" + _format_messages(rows)

    except FileNotFoundError as e:
        return f"[ERROR] {e}"
    except sqlite3.OperationalError as e:
        if "unable to open" in str(e):
            return "[ERROR] Permission denied. Grant Full Disk Access to your terminal/Python in System Settings > Privacy & Security."
        return f"[ERROR] Database error: {e}"
    except Exception as e:
        return f"[ERROR] {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
