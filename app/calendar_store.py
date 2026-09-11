"""
SQLite store for the agent's internal calendar.

This is the agent's *own* calendar — it replaces the old AppleScript bridge to
macOS Calendar.app. One table, ``calendar_events``, lives in the shared database
file (``config.DB_PATH``) but owns its own connection, mirroring db.py and
project_store.py (a module-level connection singleton + write lock +
dict-returning CRUD).

Events come in two shapes:
  - timed:   a start/end clock time on a single day (or crossing midnight)
  - all-day: a whole day, or a multi-day span like a trip (Jul 5 → Jul 8)

Start/end are stored as uniform ISO strings ``"YYYY-MM-DD HH:MM:SS"`` so that a
plain lexicographic string comparison is the same as a chronological one — which
makes day/week/range overlap queries a simple ``start_at < range_end AND
end_at > range_start``. ``end_at`` is *exclusive*: an all-day event on Jul 5 is
stored as start ``Jul 5 00:00:00`` → end ``Jul 6 00:00:00``.

Reminders tie into the existing scheduler. Setting ``reminder_minutes`` on an
event writes a one-time task into ``scheduled_tasks.json`` (the same file the
scheduler daemon reads), so the agent gets pinged before the event. Editing the
event's time or deleting it keeps that reminder in sync.
"""

import os
import json
import time
import uuid
import threading
import sqlite3
from datetime import datetime, timedelta

import config

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()
_sched_lock = threading.Lock()  # guards the shared scheduled_tasks.json file

# Stored timestamp format. Fixed width → lexicographic == chronological order.
_FMT = "%Y-%m-%d %H:%M:%S"

# All-day events have no clock time, so a reminder is measured back from this
# hour on the start date (e.g. reminder_minutes=60 → 8:00 AM on the start day).
_ALLDAY_REMINDER_HOUR = 9

# Sentinel for update_event: "this field was not supplied, leave it as-is".
_U = object()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("PRAGMA busy_timeout=5000")
        init_calendar_db(_conn)
    return _conn


def init_calendar_db(conn: sqlite3.Connection | None = None):
    """Create the calendar_events table and indexes if they don't exist."""
    conn = conn or _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            title            TEXT    NOT NULL,
            start_at         TEXT    NOT NULL,   -- "YYYY-MM-DD HH:MM:SS" inclusive
            end_at           TEXT    NOT NULL,   -- "YYYY-MM-DD HH:MM:SS" exclusive
            all_day          INTEGER NOT NULL DEFAULT 0,
            location         TEXT    NOT NULL DEFAULT '',
            notes            TEXT    NOT NULL DEFAULT '',
            reminder_minutes INTEGER,            -- NULL = no reminder
            reminder_task_id TEXT    NOT NULL DEFAULT '',
            created_at       REAL    NOT NULL,
            updated_at       REAL    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(start_at);
        CREATE INDEX IF NOT EXISTS idx_calendar_events_end   ON calendar_events(end_at);
    """)
    conn.commit()


# ---- time helpers -----------------------------------------------------------

def _fmt(dt: datetime) -> str:
    return dt.strftime(_FMT)


def _parse_day(date_str: str) -> datetime:
    """Parse YYYY-MM-DD to midnight. Empty string → today. Raises ValueError."""
    if not date_str:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return datetime.strptime(date_str, "%Y-%m-%d")


def _compute_span(start_date: str, end_date: str, start_time: str,
                  end_time: str, all_day: bool) -> tuple[datetime, datetime, bool]:
    """Resolve the raw inputs into (start_dt, end_dt_exclusive, all_day).

    Raises ValueError on bad formats.
    """
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid start_date '{start_date}'. Use YYYY-MM-DD.")

    timed = bool(start_time) and not all_day
    if timed:
        try:
            st = datetime.strptime(start_time, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid start_time '{start_time}'. Use HH:MM (24h).")
        start_dt = sd.replace(hour=st.hour, minute=st.minute, second=0, microsecond=0)
        ed = sd
        if end_date:
            try:
                ed = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid end_date '{end_date}'. Use YYYY-MM-DD.")
        if end_time:
            try:
                et = datetime.strptime(end_time, "%H:%M")
            except ValueError:
                raise ValueError(f"Invalid end_time '{end_time}'. Use HH:MM (24h).")
            end_dt = ed.replace(hour=et.hour, minute=et.minute, second=0, microsecond=0)
        else:
            end_dt = start_dt + timedelta(hours=1)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=1)
        return start_dt, end_dt, False

    # All-day (single or multi-day). end_at is exclusive → last day + 1.
    start_dt = sd.replace(hour=0, minute=0, second=0, microsecond=0)
    last = sd
    if end_date:
        try:
            last = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid end_date '{end_date}'. Use YYYY-MM-DD.")
    last = last.replace(hour=0, minute=0, second=0, microsecond=0)
    if last < start_dt:
        raise ValueError("end_date is before start_date.")
    end_dt = last + timedelta(days=1)
    return start_dt, end_dt, True


def _reminder_fire_dt(start_dt: datetime, all_day: bool, minutes: int) -> datetime:
    """When a reminder should fire: `minutes` before the event start (or before
    9:00 AM on the start date for all-day events)."""
    anchor = start_dt
    if all_day:
        anchor = start_dt.replace(hour=_ALLDAY_REMINDER_HOUR, minute=0, second=0, microsecond=0)
    return anchor - timedelta(minutes=minutes)


def _decompose(ev: dict) -> dict:
    """Break a stored event back into the raw add_event-style pieces, so
    update_event can merge partial changes over the existing values."""
    start = datetime.strptime(ev["start_at"], _FMT)
    end = datetime.strptime(ev["end_at"], _FMT)
    if ev["all_day"]:
        last = end - timedelta(days=1)
        return {"start_date": start.strftime("%Y-%m-%d"),
                "end_date": last.strftime("%Y-%m-%d"),
                "start_time": "", "end_time": "", "all_day": True}
    return {"start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "start_time": start.strftime("%H:%M"),
            "end_time": end.strftime("%H:%M"),
            "all_day": False}


# ---- scheduler reminder integration ----------------------------------------
# We read/write the same scheduled_tasks.json the scheduler daemon polls. A
# reminder is a one-time cron task ("M H D Mon *" with fixed fields → the daemon
# auto-deletes it after it fires; see is_one_time_schedule in agent/scheduler.py).

def _load_sched() -> list[dict]:
    path = config.SCHEDULED_TASKS_FILE
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_sched(tasks: list[dict]):
    path = config.SCHEDULED_TASKS_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(tasks, f, indent=2)


def _remove_scheduled_task(task_id: str):
    if not task_id:
        return
    with _sched_lock:
        tasks = _load_sched()
        kept = [t for t in tasks if t.get("id") != task_id]
        if len(kept) != len(tasks):
            _save_sched(kept)


def _create_scheduled_task(ev: dict, fire_dt: datetime) -> str:
    """Write a one-time reminder task and return its id."""
    task_id = uuid.uuid4().hex[:8]
    cron = f"{fire_dt.minute} {fire_dt.hour} {fire_dt.day} {fire_dt.month} *"
    # Built by calendar_briefing so a manually-set reminder says something as
    # useful as an auto-planned one — the rest of the day, the event's notes, and
    # a nudge about what to do, rather than reading the entry back.
    # Imported lazily: calendar_briefing imports this module.
    import calendar_briefing
    minutes = max(1, int((datetime.strptime(ev["start_at"], _FMT) - fire_dt).total_seconds() // 60))
    prompt = calendar_briefing.announcement_prompt(
        ev, minutes, "the user set a reminder for this", fire_dt)
    task = {
        "id": task_id,
        "name": f"cal_evt_{ev['id']}",
        "prompt": prompt,
        "schedule": cron,
        "notify_telegram": True,
        # Phrasing only — no tools needed (see scheduler._announce).
        "tools": False,
        # Reminders are announced aloud by the voice assistant AND sent to
        # Telegram (see delivery.py sinks; the scheduler daemon routes these).
        "sinks": ["voice", "telegram"],
        "enabled": True,
        "created_at": datetime.now().isoformat(),
        "last_run": None,
    }
    with _sched_lock:
        tasks = _load_sched()
        # Defensive: drop any stale task pointing at the same event before adding.
        tasks = [t for t in tasks if t.get("name") != task["name"]]
        tasks.append(task)
        _save_sched(tasks)
    return task_id


def _sync_reminder(event_id: int):
    """Reconcile the scheduler task for an event with its current reminder.

    Removes any previously-scheduled reminder, then (re)creates one if the event
    has reminder_minutes set and its fire time is still in the future. Persists
    the resulting task id (or "") back onto the event row.
    """
    ev = get_event(event_id)
    if not ev:
        return
    _remove_scheduled_task(ev["reminder_task_id"])

    new_task_id = ""
    minutes = ev["reminder_minutes"]
    if minutes and minutes > 0:
        start_dt = datetime.strptime(ev["start_at"], _FMT)
        fire = _reminder_fire_dt(start_dt, bool(ev["all_day"]), minutes)
        if fire > datetime.now():
            new_task_id = _create_scheduled_task(ev, fire)

    if new_task_id != ev["reminder_task_id"]:
        with _lock:
            conn = _get_conn()
            conn.execute("UPDATE calendar_events SET reminder_task_id = ? WHERE id = ?",
                         (new_task_id, event_id))
            conn.commit()


# ---- CRUD -------------------------------------------------------------------

def get_event(event_id) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM calendar_events WHERE id = ?", (int(event_id),)).fetchone()
    return dict(row) if row else None


def create_event(title: str, start_date: str, end_date: str = "", start_time: str = "",
                 end_time: str = "", all_day: bool = False, location: str = "",
                 notes: str = "", reminder_minutes: int | None = None) -> dict:
    """Insert an event. Raises ValueError on bad input."""
    title = title.strip()
    if not title:
        raise ValueError("Event title is required.")
    start_dt, end_dt, all_day = _compute_span(start_date, end_date, start_time, end_time, all_day)
    rm = reminder_minutes if (reminder_minutes and reminder_minutes > 0) else None
    now = time.time()
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "INSERT INTO calendar_events (title, start_at, end_at, all_day, location, notes, "
            "reminder_minutes, reminder_task_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, ?)",
            (title, _fmt(start_dt), _fmt(end_dt), int(all_day), location.strip(),
             notes.strip(), rm, now, now),
        )
        conn.commit()
        event_id = cur.lastrowid
    if rm is not None:
        _sync_reminder(event_id)
    return get_event(event_id)


def update_event(event_id, title=_U, start_date=_U, end_date=_U, start_time=_U,
                 end_time=_U, all_day=_U, location=_U, notes=_U, reminder_minutes=_U) -> dict | None:
    """Update an event. Unsupplied fields (the _U sentinel) are left unchanged.
    reminder_minutes: None clears the reminder, a positive int sets it."""
    ev = get_event(event_id)
    if not ev:
        return None

    sets: dict = {}
    if title is not _U:
        title = title.strip()
        if not title:
            raise ValueError("Event title cannot be empty.")
        sets["title"] = title
    if location is not _U:
        sets["location"] = location.strip()
    if notes is not _U:
        sets["notes"] = notes.strip()

    span_changed = any(x is not _U for x in (start_date, end_date, start_time, end_time, all_day))
    if span_changed:
        cur = _decompose(ev)
        sd = start_date if start_date is not _U else cur["start_date"]
        ed = end_date if end_date is not _U else cur["end_date"]
        stime = start_time if start_time is not _U else cur["start_time"]
        etime = end_time if end_time is not _U else cur["end_time"]
        ad = all_day if all_day is not _U else cur["all_day"]
        start_dt, end_dt, ad = _compute_span(sd, ed, stime, etime, ad)
        sets["start_at"] = _fmt(start_dt)
        sets["end_at"] = _fmt(end_dt)
        sets["all_day"] = int(ad)

    reminder_changed = reminder_minutes is not _U
    if reminder_changed:
        sets["reminder_minutes"] = reminder_minutes if (reminder_minutes and reminder_minutes > 0) else None

    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        with _lock:
            conn = _get_conn()
            conn.execute(
                f"UPDATE calendar_events SET {cols}, updated_at = ? WHERE id = ?",
                [*sets.values(), time.time(), int(event_id)],
            )
            conn.commit()

    # The reminder fire time depends on the start time, so re-sync if either moved.
    if span_changed or reminder_changed:
        _sync_reminder(int(event_id))
    return get_event(event_id)


def delete_event(event_id) -> dict | None:
    """Delete an event (and its reminder). Returns the deleted row, or None."""
    ev = get_event(event_id)
    if not ev:
        return None
    _remove_scheduled_task(ev["reminder_task_id"])
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM calendar_events WHERE id = ?", (int(event_id),))
        conn.commit()
    return ev


def events_in_range(range_start: datetime, range_end: datetime) -> list[dict]:
    """Events overlapping [range_start, range_end). Multi-day events that span
    into the window are included."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM calendar_events WHERE start_at < ? AND end_at > ? ORDER BY start_at",
        (_fmt(range_end), _fmt(range_start)),
    ).fetchall()
    return [dict(r) for r in rows]


# ---- rendering --------------------------------------------------------------

def _when_phrase(ev: dict) -> str:
    start = datetime.strptime(ev["start_at"], _FMT)
    end = datetime.strptime(ev["end_at"], _FMT)
    if ev["all_day"]:
        last = end - timedelta(days=1)
        if last.date() == start.date():
            return f"{start:%a %Y-%m-%d} (all day)"
        return f"{start:%a %Y-%m-%d} → {last:%a %Y-%m-%d} (all day)"
    if start.date() == end.date():
        return f"{start:%a %Y-%m-%d} {start:%H:%M}–{end:%H:%M}"
    return f"{start:%a %Y-%m-%d %H:%M} → {end:%a %Y-%m-%d %H:%M}"


def format_event(ev: dict) -> str:
    """One readable block for an event (used in confirmations and listings)."""
    parts = [f"[{ev['id']}] {ev['title']} — {_when_phrase(ev)}"]
    tail = []
    if ev["location"]:
        tail.append(f"@ {ev['location']}")
    if ev["reminder_minutes"]:
        tail.append(f"⏰ {ev['reminder_minutes']}m before")
    if tail:
        parts.append("      " + "  ".join(tail))
    if ev["notes"]:
        parts.append(f"      {ev['notes']}")
    return "\n".join(parts)


def reminder_status(ev: dict) -> str:
    """Trailing note describing whether a reminder was actually scheduled."""
    minutes = ev["reminder_minutes"]
    if not minutes or minutes <= 0:
        return ""
    start = datetime.strptime(ev["start_at"], _FMT)
    fire = _reminder_fire_dt(start, bool(ev["all_day"]), minutes)
    if ev["reminder_task_id"]:
        return f"\n⏰ Reminder scheduled for {fire:%a %Y-%m-%d %H:%M}."
    return (f"\n⏰ Reminder time ({fire:%Y-%m-%d %H:%M}) is already in the past — "
            "not scheduled.")


def render_events(events: list[dict], label: str) -> str:
    if not events:
        return f"No {label}."
    header = f"{len(events)} {'event' if len(events) == 1 else 'events'} {label}:"
    return header + "\n" + "\n".join(format_event(e) for e in events)


# ---- day / week / range views (used by the MCP server) ----------------------

def day_view(date_str: str = "") -> str:
    day = _parse_day(date_str)
    events = events_in_range(day, day + timedelta(days=1))
    return render_events(events, f"on {day:%a %Y-%m-%d}")


def week_view(date_str: str = "") -> str:
    day = _parse_day(date_str)
    monday = day - timedelta(days=day.weekday())          # Monday of that week
    return render_events(
        events_in_range(monday, monday + timedelta(days=7)),
        f"in the week of {monday:%Y-%m-%d} (Mon–Sun)",
    )


def range_view(start_date: str, end_date: str) -> str:
    start = _parse_day(start_date)
    end = _parse_day(end_date)
    if end < start:
        raise ValueError("end_date is before start_date.")
    return render_events(
        events_in_range(start, end + timedelta(days=1)),
        f"from {start:%Y-%m-%d} to {end:%Y-%m-%d}",
    )
