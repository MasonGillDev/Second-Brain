"""
Pending iMessage reply watches.

When the agent texts someone to find something out ("ask Char where dinner is"),
the answer arrives minutes or hours later, in a separate process, long after the
tool call returned. A watch records the question and the follow-up intent, and a
poll loop in the dashboard wakes the agent when the reply actually lands.

Correlating a reply to the right question is the whole problem, and three things
make it precise:

  * A ROWID watermark taken BEFORE the send. Every later message has a higher
    ROWID, so a watch can never match something already in the thread.
  * The contact's own handles, so two concurrent watches on different people
    can't cross, and only inbound messages (is_from_me = 0) count.
  * A settle window. People text in bursts — "let me check" then "7:30 at Aba"
    a minute later. Firing on the first inbound message would act on the wrong
    half of the answer, so the first reply starts a timer and the whole burst is
    delivered together.

Watches outlive restarts (SQLite, same database as logs/costs) and expire on
their own so a question nobody answers doesn't wait forever.
"""

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import config
import imessage_store

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()

POLL_SECONDS = getattr(config, "REPLY_WATCH_POLL_SECONDS", 20)
SETTLE_SECONDS = getattr(config, "REPLY_WATCH_SETTLE_SECONDS", 45)
DEFAULT_EXPIRE_HOURS = getattr(config, "REPLY_WATCH_EXPIRE_HOURS", 24)


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        # WAL: the MCP server process writes watches while the dashboard polls them.
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=5000")
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS reply_watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_name TEXT NOT NULL,
                handles TEXT NOT NULL,          -- JSON list
                after_rowid INTEGER NOT NULL,   -- watermark: only later messages match
                question TEXT NOT NULL,
                intent TEXT NOT NULL,
                sinks TEXT NOT NULL,            -- JSON list
                status TEXT NOT NULL,           -- pending | fired | expired | cancelled
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                first_reply_at REAL,            -- start of the settle window
                fired_at REAL,
                reply_text TEXT
            )
        """)
        _conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_watch_status ON reply_watches(status)")
        _conn.commit()
    return _conn


def current_watermark() -> int:
    """Highest message ROWID right now — the boundary a reply must exceed."""
    conn = imessage_store._chat_db()
    try:
        row = conn.execute("SELECT MAX(ROWID) mx FROM message").fetchone()
        return row["mx"] or 0
    finally:
        conn.close()


def create_watch(contact_name: str, handles: list[str], question: str, intent: str,
                 after_rowid: int, sinks: list[str] | None = None,
                 expire_hours: float = DEFAULT_EXPIRE_HOURS) -> dict:
    now = time.time()
    with _lock:
        conn = _get_conn()
        cur = conn.execute("""
            INSERT INTO reply_watches
              (contact_name, handles, after_rowid, question, intent, sinks,
               status, created_at, expires_at)
            VALUES (?,?,?,?,?,?,'pending',?,?)
        """, (contact_name, json.dumps(handles), after_rowid, question, intent,
              json.dumps(sinks or ["telegram", "voice"]), now,
              now + expire_hours * 3600))
        conn.commit()
        watch_id = cur.lastrowid
    return {"id": watch_id, "contact_name": contact_name, "question": question,
            "intent": intent, "expires_at": now + expire_hours * 3600}


def pending() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM reply_watches WHERE status='pending' ORDER BY created_at"
    ).fetchall()
    return [dict(r) for r in rows]


def cancel(watch_id: int) -> bool:
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "UPDATE reply_watches SET status='cancelled' WHERE id=? AND status='pending'",
            (watch_id,))
        conn.commit()
        return cur.rowcount > 0


def _new_messages(watch: dict) -> list[dict]:
    """Inbound messages from this contact that arrived after the watermark."""
    handles = json.loads(watch["handles"])
    if not handles:
        return []
    marks = ",".join("?" * len(handles))
    conn = imessage_store._chat_db()
    try:
        rows = conn.execute(f"""
            {imessage_store._BASE_SELECT}
            WHERE m.ROWID > ?
              AND m.is_from_me = 0
              AND cmj.chat_id IN (
                    SELECT chj.chat_id FROM chat_handle_join chj
                    JOIN handle h2 ON h2.ROWID = chj.handle_id
                    WHERE h2.id IN ({marks})
                  )
              AND (SELECT COUNT(*) FROM chat_handle_join
                    WHERE chat_id = cmj.chat_id) = 1
            ORDER BY m.date
        """, [watch["after_rowid"]] + handles).fetchall()
        return [imessage_store._row_to_message(r) for r in rows]
    finally:
        conn.close()


def _mark(watch_id: int, **fields):
    sets = ", ".join(f"{k}=?" for k in fields)
    with _lock:
        conn = _get_conn()
        conn.execute(f"UPDATE reply_watches SET {sets} WHERE id=?",
                     list(fields.values()) + [watch_id])
        conn.commit()


def check_due() -> tuple[list[dict], list[dict]]:
    """
    One poll tick.

    Returns (ready, expired). A watch becomes ready once a reply has landed AND
    the settle window has passed, so a burst of messages is delivered as one
    answer rather than firing on "let me check".
    """
    now = time.time()
    ready, expired = [], []

    for watch in pending():
        try:
            messages = _new_messages(watch)
        except imessage_store.MessageError:
            continue  # unreadable right now; try again next tick

        if not messages:
            if now > watch["expires_at"]:
                _mark(watch["id"], status="expired")
                expired.append(watch)
            continue

        if not watch["first_reply_at"]:
            _mark(watch["id"], first_reply_at=now)
            watch["first_reply_at"] = now

        # Let the burst finish before acting on it.
        if now - watch["first_reply_at"] < SETTLE_SECONDS:
            continue

        reply_text = "\n".join(m["text"] for m in messages)
        _mark(watch["id"], status="fired", fired_at=now, reply_text=reply_text)
        ready.append({**watch, "reply_text": reply_text, "messages": messages})

    return ready, expired


def build_prompt(watch: dict) -> str:
    """The wake-up prompt: what was asked, what came back, what to do about it."""
    when = datetime.fromtimestamp(watch["created_at"]).strftime("%I:%M %p").lstrip("0")
    return (
        f"You texted {watch['contact_name']} at {when} and asked: "
        f"\"{watch['question']}\"\n\n"
        f"{watch['contact_name']} has now replied:\n{watch['reply_text']}\n\n"
        f"Your follow-up task is: {watch['intent']}\n\n"
        "Carry that out now using your tools. If the reply actually answers the "
        "question, act on it. If it does not (they deflected, asked something "
        "back, or said they'd find out later), do NOT invent an answer — just say "
        "what they said and what you're waiting on. Reply in one or two short "
        "sentences suitable for reading aloud."
    )


def send_and_watch(to: str, text: str, intent: str, confirm: bool = False,
                   sinks: list[str] | None = None,
                   expire_hours: float = DEFAULT_EXPIRE_HOURS) -> dict:
    """
    Send a message and register a watch for the reply.

    The watermark is taken BEFORE sending: a reply that somehow arrives while the
    send is still in flight must still count, and our own outgoing message is
    excluded by is_from_me anyway.
    """
    if not intent or not intent.strip():
        raise imessage_store.MessageError(
            "await_reply needs an intent — what to do once they answer.")

    watermark = current_watermark()
    result = imessage_store.send_message(to, text, confirm=confirm)
    if not result["sent"]:
        return {**result, "watch": None}

    watch = create_watch(
        contact_name=result["name"], handles=[result["handle"]],
        question=text, intent=intent, after_rowid=watermark,
        sinks=sinks, expire_hours=expire_hours)
    return {**result, "watch": watch}


async def watch_loop(run_prompt):
    """
    Poll pending watches and wake the agent when a reply lands.

    `run_prompt` is injected (the dashboard passes TriggerEngine.run_prompt) so
    this module stays free of the agent and keeps the single-AgentCore lock that
    the trigger engine already owns.

    Fully guarded: a watch that blows up must not kill the loop, or every later
    reply is silently lost.
    """
    import asyncio

    import delivery

    print(f"  [reply-watch] Loop started (tick {POLL_SECONDS}s, "
          f"settle {SETTLE_SECONDS}s)")
    while True:
        try:
            ready, expired = check_due()

            for watch in ready:
                sinks = json.loads(watch["sinks"])
                print(f"  [reply-watch] {watch['contact_name']} replied "
                      f"(watch {watch['id']}) — waking agent")
                try:
                    result = await run_prompt(build_prompt(watch), source="reply_watch")
                    await delivery.deliver(sinks, result)
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    print(f"  [reply-watch] watch {watch['id']} failed: {err}")
                    # The reply itself still matters even if the follow-up failed.
                    await delivery.deliver(
                        [s for s in sinks if s != "silent"],
                        f"⚠️ {watch['contact_name']} replied "
                        f"(\"{watch['reply_text'][:200]}\") but the follow-up failed: {err}")

            for watch in expired:
                hours = (watch["expires_at"] - watch["created_at"]) / 3600
                print(f"  [reply-watch] watch {watch['id']} expired after {hours:.0f}h")
                await delivery.deliver(
                    [s for s in json.loads(watch["sinks"]) if s != "voice"],
                    f"⏳ No reply from {watch['contact_name']} after {hours:.0f}h — "
                    f"gave up waiting on: {watch['question'][:160]}")
        except Exception as e:
            print(f"  [reply-watch] loop error: {type(e).__name__}: {e}")
        await asyncio.sleep(POLL_SECONDS)
