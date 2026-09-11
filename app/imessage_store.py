"""
Read-only access to the local iMessage database (~/Library/Messages/chat.db).

Three things about chat.db make the naive query wrong, and all three bite hard:

  1. `message.text` is NULL on modern macOS — the text lives in `attributedBody`,
     an NSAttributedString typedstream blob. Reading `text` alone returns almost
     nothing (498 of the 500 most recent messages here are NULL).
  2. `message.handle_id` is 0 for messages you SENT (83801 of 86066 here), so any
     join through `handle` silently drops your own side of every conversation.
     Scope through chat_message_join instead.
  3. Handles are phone numbers and emails. Matching a name like "Char" against
     them finds whoever happens to have those letters in their email address, not
     the person. Names come from the Contacts database, joined on the handle.

Requires Full Disk Access for the running process.
"""

import glob
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")
ADDRESSBOOK_GLOB = os.path.expanduser(
    "~/Library/Application Support/AddressBook/**/AddressBook-v22.abcddb"
)

# iMessage timestamps are nanoseconds since 2001-01-01 UTC.
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)

_contacts_cache: dict | None = None


class MessageError(RuntimeError):
    """Something the caller should show the user verbatim."""


# --------------------------------------------------------------------------
# database access
# --------------------------------------------------------------------------

def _connect(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        raise MessageError(f"Database not found at {path}")
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        raise MessageError(f"Could not open {os.path.basename(path)}: {e}")
    conn.row_factory = sqlite3.Row
    return conn


def _chat_db() -> sqlite3.Connection:
    try:
        conn = _connect(CHAT_DB)
        conn.execute("SELECT 1 FROM message LIMIT 1")
        return conn
    except sqlite3.OperationalError as e:
        if "unable to open" in str(e) or "authorization" in str(e):
            raise MessageError(
                "Permission denied reading iMessage. Grant Full Disk Access to the "
                "process in System Settings > Privacy & Security > Full Disk Access."
            )
        raise MessageError(f"Database error: {e}")


# --------------------------------------------------------------------------
# message text
# --------------------------------------------------------------------------

def decode_body(blob: bytes | None) -> str | None:
    """
    Pull the plain string out of an NSAttributedString typedstream blob.

    Not a full typedstream parser: the archive puts the message string right after
    the NSString class marker, length-prefixed (one byte, or 0x81 + uint16 when it
    exceeds 127). That covers every message in practice.
    """
    if not blob:
        return None
    try:
        body = blob.split(b"NSString", 1)[1][5:]
        if body[0] == 0x81:
            length = int.from_bytes(body[1:3], "little")
            body = body[3:]
        else:
            length = body[0]
            body = body[1:]
        return body[:length].decode("utf-8", errors="replace") or None
    except (IndexError, UnicodeDecodeError):
        return None


def message_text(row: sqlite3.Row) -> str:
    """Best available text for a message row, falling back to a content hint."""
    text = row["text"] if "text" in row.keys() else None
    if not text:
        text = decode_body(row["attributedBody"] if "attributedBody" in row.keys() else None)
    if text:
        return text.replace("￼", "").strip() or "(attachment)"
    return "(attachment or reaction)"


def to_datetime(apple_ns: int | None) -> datetime | None:
    if not apple_ns:
        return None
    try:
        return (APPLE_EPOCH + timedelta(seconds=apple_ns / 1_000_000_000)).astimezone()
    except (ValueError, OverflowError, OSError):
        return None


def format_date(apple_ns: int | None) -> str:
    dt = to_datetime(apple_ns)
    return dt.strftime("%Y-%m-%d %I:%M %p").replace(" 0", " ") if dt else "unknown"


# --------------------------------------------------------------------------
# contacts
# --------------------------------------------------------------------------

def normalize_handle(handle: str) -> str:
    """Phone numbers vary by formatting; compare on the last 10 digits."""
    handle = (handle or "").strip()
    if "@" in handle:
        return handle.lower()
    digits = re.sub(r"\D", "", handle)
    return digits[-10:] if len(digits) >= 10 else digits


def load_contacts(refresh: bool = False) -> dict[str, str]:
    """Map normalized handle -> display name, from every Contacts source."""
    global _contacts_cache
    if _contacts_cache is not None and not refresh:
        return _contacts_cache

    contacts: dict[str, str] = {}
    for path in glob.glob(ADDRESSBOOK_GLOB, recursive=True):
        try:
            conn = _connect(path)
        except MessageError:
            continue
        try:
            for table, column in (("ZABCDPHONENUMBER", "ZFULLNUMBER"),
                                  ("ZABCDEMAILADDRESS", "ZADDRESS")):
                rows = conn.execute(f"""
                    SELECT r.ZFIRSTNAME first, r.ZLASTNAME last,
                           r.ZORGANIZATION org, v.{column} handle
                    FROM {table} v JOIN ZABCDRECORD r ON v.ZOWNER = r.Z_PK
                    WHERE v.{column} IS NOT NULL
                """).fetchall()
                for row in rows:
                    name = " ".join(p for p in (row["first"], row["last"]) if p).strip()
                    name = name or (row["org"] or "").strip()
                    key = normalize_handle(row["handle"])
                    # Longer names are usually the fuller record of the same person.
                    if name and key and len(name) > len(contacts.get(key, "")):
                        contacts[key] = name
        except sqlite3.OperationalError:
            continue
        finally:
            conn.close()

    _contacts_cache = contacts
    return contacts


def display_name(handle: str) -> str:
    """Contact name for a handle, or the raw handle when there's no card."""
    if not handle:
        return "Unknown"
    return load_contacts().get(normalize_handle(handle), handle)


def find_handles(query: str, conn: sqlite3.Connection) -> tuple[list[str], str, list[str]]:
    """
    Resolve a name or handle to the handles to search.

    Returns (handles, matched_name, other_candidate_names). Ambiguity is real —
    "char" matches Char, Charlie, Charly and Chars Sister here — so candidates are
    ranked exact > prefix > substring, then by who you've messaged most recently,
    and the runners-up come back so the caller can offer them.
    """
    query = (query or "").strip()
    if not query:
        return [], "", []

    known = {h["id"] for h in conn.execute("SELECT DISTINCT id FROM handle")}

    # A literal phone number or email: match it directly.
    if "@" in query or re.fullmatch(r"[\d\s+()\-.]{7,}", query):
        target = normalize_handle(query)
        hits = [h for h in known if normalize_handle(h) == target]
        if hits:
            return hits, display_name(hits[0]), []

    # Otherwise treat it as a name and go through Contacts.
    lowered = query.lower()
    contacts = load_contacts()
    by_name: dict[str, list[str]] = {}
    for handle in known:
        name = contacts.get(normalize_handle(handle))
        if not name:
            continue
        low = name.lower()
        rank = 0 if low == lowered else 1 if low.startswith(lowered) else 2 if lowered in low else None
        if rank is not None:
            by_name.setdefault(name, []).append(handle)

    if not by_name:
        return [], "", []

    # Rank: match quality, then most recent DIRECT conversation, then closeness of
    # name. Measuring any chat would tie two people who share a group thread —
    # which is exactly how "Chars Sister" outranked "Char" here.
    def last_seen(handles: list[str]) -> int:
        marks = ",".join("?" * len(handles))
        row = conn.execute(f"""
            SELECT MAX(m.date) mx FROM message m
            JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
            JOIN chat_handle_join chj ON chj.chat_id = cmj.chat_id
            JOIN handle h ON h.ROWID = chj.handle_id
            WHERE h.id IN ({marks})
              AND (SELECT COUNT(*) FROM chat_handle_join
                    WHERE chat_id = cmj.chat_id) = 1
        """, handles).fetchone()
        return row["mx"] or 0

    def sort_key(item):
        name, handles = item
        low = name.lower()
        rank = 0 if low == lowered else 1 if low.startswith(lowered) else 2
        # "Char" beats "Chars Sister" for the query "char": fewer extra characters.
        return (rank, -last_seen(handles), len(name))

    ordered = sorted(by_name.items(), key=sort_key)
    best_name, best_handles = ordered[0]
    return best_handles, best_name, [n for n, _ in ordered[1:5]]


# --------------------------------------------------------------------------
# queries
# --------------------------------------------------------------------------

# Scoping through chat_message_join (not handle_id) is what keeps sent messages in.
_BASE_SELECT = """
    SELECT m.ROWID, m.text, m.attributedBody, m.date, m.is_from_me, m.is_read,
           h.id AS handle, ch.ROWID AS chat_id, ch.display_name AS chat_name,
           (SELECT COUNT(*) FROM chat_handle_join WHERE chat_id = ch.ROWID) AS members
    FROM message m
    JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
    JOIN chat ch ON ch.ROWID = cmj.chat_id
    LEFT JOIN handle h ON h.ROWID = m.handle_id
"""


def _chat_filter(handles: list[str], include_groups: bool) -> tuple[str, list]:
    marks = ",".join("?" * len(handles))
    clause = f"""
        cmj.chat_id IN (
            SELECT chj.chat_id FROM chat_handle_join chj
            JOIN handle h2 ON h2.ROWID = chj.handle_id
            WHERE h2.id IN ({marks})
        )
    """
    if not include_groups:
        # A 1:1 thread has exactly one participant besides you.
        clause += """
        AND (SELECT COUNT(*) FROM chat_handle_join WHERE chat_id = cmj.chat_id) = 1
        """
    return clause, list(handles)


def recent_messages(contact: str = "", count: int = 20,
                    include_groups: bool = False) -> dict:
    conn = _chat_db()
    try:
        if contact:
            handles, name, others = find_handles(contact, conn)
            if not handles:
                raise MessageError(
                    f"No conversation found for '{contact}'. Try a contact name as it "
                    "appears in Contacts, or a phone number/email."
                )
            where, params = _chat_filter(handles, include_groups)
            rows = conn.execute(
                f"{_BASE_SELECT} WHERE {where} ORDER BY m.date DESC LIMIT ?",
                params + [count],
            ).fetchall()
            if not rows and not include_groups:
                where, params = _chat_filter(handles, True)
                rows = conn.execute(
                    f"{_BASE_SELECT} WHERE {where} ORDER BY m.date DESC LIMIT ?",
                    params + [count],
                ).fetchall()
        else:
            name, others = "", []
            rows = conn.execute(
                f"{_BASE_SELECT} ORDER BY m.date DESC LIMIT ?", (count,)
            ).fetchall()
        return {"name": name, "others": others,
                "messages": [_row_to_message(r) for r in reversed(rows)]}
    finally:
        conn.close()


def search(query: str, contact: str = "", count: int = 20,
           include_groups: bool = True) -> dict:
    conn = _chat_db()
    try:
        # The blob stores text as UTF-8, so a LIKE on it is a usable prefilter;
        # the decoded text is what actually confirms the hit.
        like = f"%{query}%"
        clauses = ["(m.text LIKE ? OR CAST(m.attributedBody AS TEXT) LIKE ?)"]
        params: list = [like, like]
        name, others = "", []

        if contact:
            handles, name, others = find_handles(contact, conn)
            if not handles:
                raise MessageError(f"No conversation found for '{contact}'.")
            clause, chat_params = _chat_filter(handles, include_groups)
            clauses.append(clause)
            params += chat_params

        rows = conn.execute(
            f"{_BASE_SELECT} WHERE {' AND '.join(clauses)} ORDER BY m.date DESC LIMIT ?",
            params + [count * 3],
        ).fetchall()

        hits = []
        for row in rows:
            message = _row_to_message(row)
            if query.lower() in message["text"].lower():
                hits.append(message)
            if len(hits) >= count:
                break
        return {"name": name, "others": others, "messages": list(reversed(hits))}
    finally:
        conn.close()


def unread() -> list[dict]:
    conn = _chat_db()
    try:
        rows = conn.execute(f"""
            {_BASE_SELECT}
            WHERE m.is_read = 0 AND m.is_from_me = 0
            ORDER BY m.date DESC LIMIT 50
        """).fetchall()
        return [_row_to_message(r) for r in reversed(rows)]
    finally:
        conn.close()


def conversations(count: int = 20) -> list[dict]:
    """Most recently active threads, newest first."""
    conn = _chat_db()
    try:
        rows = conn.execute("""
            SELECT ch.ROWID chat_id, ch.display_name chat_name,
                   MAX(m.date) last_date,
                   (SELECT COUNT(*) FROM chat_handle_join WHERE chat_id = ch.ROWID) members,
                   (SELECT h.id FROM chat_handle_join chj JOIN handle h ON h.ROWID = chj.handle_id
                     WHERE chj.chat_id = ch.ROWID LIMIT 1) handle,
                   SUM(m.is_read = 0 AND m.is_from_me = 0) unread
            FROM chat ch
            JOIN chat_message_join cmj ON cmj.chat_id = ch.ROWID
            JOIN message m ON m.ROWID = cmj.message_id
            GROUP BY ch.ROWID ORDER BY last_date DESC LIMIT ?
        """, (count,)).fetchall()
        out = []
        for row in rows:
            title = row["chat_name"] or display_name(row["handle"])
            if row["members"] > 1 and not row["chat_name"]:
                title = f"Group ({row['members']} people)"
            out.append({"name": title, "date": format_date(row["last_date"]),
                        "unread": row["unread"] or 0, "group": row["members"] > 1})
        return out
    finally:
        conn.close()


def _row_to_message(row: sqlite3.Row) -> dict:
    is_group = row["members"] > 1
    return {
        "text": message_text(row),
        "date": format_date(row["date"]),
        "from_me": bool(row["is_from_me"]),
        "sender": "Me" if row["is_from_me"] else display_name(row["handle"]),
        "unread": not row["is_from_me"] and not row["is_read"],
        "chat": row["chat_name"] or ("Group" if is_group else None),
        "group": is_group,
    }
