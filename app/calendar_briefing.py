"""
Proactive calendar heads-ups.

The existing reminder path (calendar_store._sync_reminder) only fires when the
user explicitly sets reminder_minutes on an event, and announces the event by
name. This module covers the other half: deciding *on its own* which upcoming
events are worth a heads-up, how far ahead, and what the useful thing to say is
("dinner's at 6 and she said dress nice — worth starting to get ready").

Two halves, deliberately split:

  * Judgment is the LLM's. Which events deserve a nudge, and how much lead time
    something needs, is exactly the fuzzy call a model is good at — and it's the
    reason this isn't a fixed "N minutes before everything" rule.
  * Time arithmetic is Python's. Models are unreliable at turning "30 minutes
    before 6pm on Friday" into a cron field, and a wrong one fires at 3am.

Planning is re-run whenever the upcoming schedule actually changes (fingerprint),
not on a timer, so adding an event gets a plan within minutes while an unchanged
day costs nothing.

Events that already have a manual reminder are left alone — the user set that
lead time deliberately, and planning a second announcement beside it would just
talk over itself.
"""

import asyncio
import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timedelta

import calendar_store as cs
import config

# How far ahead to plan. Long enough to cover an evening plus tomorrow morning.
WINDOW_HOURS = getattr(config, "BRIEFING_WINDOW_HOURS", 18)
# How often to re-check whether the schedule changed (cheap: no LLM call).
CHECK_SECONDS = getattr(config, "BRIEFING_CHECK_SECONDS", 300)
# Re-plan at least this often even when nothing changed, so a plan made
# yesterday for "tomorrow" gets revisited with fresh context.
MAX_PLAN_AGE_HOURS = getattr(config, "BRIEFING_MAX_PLAN_AGE_HOURS", 6)
# Scheduler tasks this module owns. Distinct from calendar_store's "cal_evt_"
# so the two never clobber each other.
TASK_PREFIX = "cal_brief_"     # advance heads-up, lead time chosen by the planner
START_PREFIX = "cal_start_"    # "it's time" notice, fired at the event's start

# Every timed event gets the at-start notice — that one is "it's time", not
# advice, so it isn't the planner's call. All-day events are excluded: there is
# no moment for them to start at. Set False to only ever hear planned heads-ups.
ANNOUNCE_AT_START = getattr(config, "BRIEFING_ANNOUNCE_AT_START", True)

_plan_lock = threading.Lock()

_PLANNER_SYSTEM = (
    "You plan when someone should be given a spoken heads-up about their calendar. "
    "Respond with a SINGLE valid JSON object and nothing else."
)


def upcoming(window_hours: int = WINDOW_HOURS) -> list[dict]:
    """Events starting inside the planning window (already-started ones excluded)."""
    now = datetime.now()
    events = cs.events_in_range(now, now + timedelta(hours=window_hours))
    out = []
    for ev in events:
        start = datetime.strptime(ev["start_at"], cs._FMT)
        if start > now:
            out.append(ev)
    return out


def fingerprint(events: list[dict]) -> str:
    """Identity of the upcoming schedule — changes when anything relevant changes."""
    payload = [
        (e["id"], e["title"], e["start_at"], e["end_at"], e["location"] or "",
         e["notes"] or "", e["reminder_minutes"] or 0)
        for e in events
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _describe(ev: dict) -> str:
    bits = [f'id={ev["id"]} "{ev["title"]}" {cs._when_phrase(ev)}']
    if ev["location"]:
        bits.append(f'location: {ev["location"]}')
    if ev["notes"]:
        bits.append(f'notes: {ev["notes"]}')
    if ev["reminder_minutes"]:
        bits.append(f'ALREADY has a manual reminder {ev["reminder_minutes"]}m before')
    return " | ".join(bits)


def _planner_prompt(events: list[dict]) -> str:
    now = datetime.now()
    listing = "\n".join(f"  - {_describe(e)}" for e in events)
    return f"""It is {now:%A %Y-%m-%d %H:%M}.

Here is what's on the calendar in the next {WINDOW_HOURS} hours:
{listing}

Decide which of these deserve a proactive spoken heads-up beforehand, and how
many minutes ahead.

Be selective. A heads-up is worth it when there is something to DO before the
event — travel, changing clothes, prep, buying something, leaving the house. It
is not worth it for things that need no preparation, things already in progress,
or routine blocks the person obviously knows about.

Choose the lead time from what actually has to happen first: a dinner across
town someone has to dress for needs more lead than a call from their desk.

SKIP any event marked as already having a manual reminder — that one is already
handled, and a second announcement would talk over it.

Respond with JSON exactly like:
{{"announcements": [
  {{"event_id": 41, "lead_minutes": 45, "reason": "needs to shower and change, and it's a 20 min drive"}}
]}}

"reason" is a short note to yourself about what the person needs to do — it is
not read aloud. Return an empty list if nothing warrants a heads-up."""


async def decide(events: list[dict]) -> list[dict]:
    """Ask the model which events to announce. Returns validated decisions."""
    import workflow_runner

    candidates = [e for e in events if not e["reminder_minutes"]]
    if not candidates:
        return []

    adapter = workflow_runner._make_adapter()
    resp = await adapter.chat(
        _PLANNER_SYSTEM,
        [{"role": "user", "content": _planner_prompt(events)}],
        None,
    )
    data = workflow_runner._parse_json_object((resp.text or "").strip())
    if not data:
        print("  [briefing] planner returned no usable JSON — skipping this pass")
        return []

    by_id = {e["id"]: e for e in candidates}
    decisions = []
    for item in data.get("announcements") or []:
        try:
            event_id = int(item["event_id"])
            lead = int(item["lead_minutes"])
        except (KeyError, TypeError, ValueError):
            continue
        # Only for events we actually offered, and never for one the user already
        # set a reminder on — the model is told to skip those, but enforce it.
        if event_id not in by_id or lead <= 0:
            continue
        decisions.append({"event": by_id[event_id], "lead_minutes": lead,
                          "reason": str(item.get("reason") or "").strip()})
    return decisions


def _day_context(event: dict) -> str:
    """The rest of the day around an event — what makes the advice specific."""
    start = datetime.strptime(event["start_at"], cs._FMT)
    others = [e for e in cs.events_in_range(start - timedelta(hours=12),
                                            start + timedelta(hours=14))
              if e["id"] != event["id"]]
    if not others:
        return "Nothing else on the calendar around it."
    return "Also on the calendar around it:\n" + "\n".join(
        f"  - {e['title']} — {cs._when_phrase(e)}"
        + (f" @ {e['location']}" if e["location"] else "")
        for e in others)


def announcement_prompt(event: dict, lead_minutes: int, reason: str,
                        fire_at: datetime) -> str:
    start = datetime.strptime(event["start_at"], cs._FMT)
    return f"""Give the user a short spoken heads-up about an upcoming calendar event.

Event: "{event['title']}"
Starts: {start:%A %-I:%M %p} ({lead_minutes} minutes after this heads-up was scheduled for {fire_at:%-I:%M %p})
{f"Location: {event['location']}" if event['location'] else ""}
{f"Notes on the event: {event['notes']}" if event['notes'] else ""}

Why this heads-up was scheduled: {reason or "it needs some lead time"}

{_day_context(event)}

Say the useful thing, not the obvious one. The user knows what's on their
calendar; what they want is the nudge — what to start doing now, what to bring,
when to leave. Use the notes and the rest of the day to make it specific.

One or two sentences, conversational, spoken aloud. No preamble, no "reminder:"
prefix, no reading the calendar entry back verbatim.

IMPORTANT: check the current time before you speak. If the event has already
started or is only a few minutes away, this heads-up is running late — say
something that still makes sense at the actual current time (or that they're
already due) rather than telling them to start getting ready."""


def start_announcement_prompt(event: dict) -> str:
    """The "it's time" notification, fired at the event's start."""
    start = datetime.strptime(event["start_at"], cs._FMT)
    return f"""Tell the user that something on their calendar is starting right now.

Event: "{event['title']}"
Starts: {start:%A %-I:%M %p} — that is NOW
{f"Location: {event['location']}" if event['location'] else ""}
{f"Notes on the event: {event['notes']}" if event['notes'] else ""}

{_day_context(event)}

This is the "it's time" nudge, not a preview — they were already told it was
coming. Keep it to one short sentence. Say what is starting and the single most
useful detail with it (where to be, what follows it, what to bring). Do not
recite the calendar entry or repeat advice about getting ready.

Conversational, spoken aloud, no preamble.

IMPORTANT: check the current time. If this is firing noticeably late, say it
started at its time rather than that it is starting now."""


def _event_id_from_task(name: str) -> int | None:
    for prefix in (TASK_PREFIX, START_PREFIX):
        if name.startswith(prefix):
            try:
                return int(name[len(prefix):].split("_")[0])
            except (ValueError, IndexError):
                return None
    return None


def clear_planned(event_ids: set[int] | None = None):
    """Drop this module's not-yet-fired tasks so a re-plan is idempotent."""
    with cs._sched_lock:
        tasks = cs._load_sched()
        kept = []
        for t in tasks:
            event_id = _event_id_from_task(t.get("name", ""))
            if event_id is None:                      # not ours — never touch it
                kept.append(t)
            elif event_ids is not None and event_id not in event_ids:
                kept.append(t)
        if len(kept) != len(tasks):
            cs._save_sched(kept)
        return len(tasks) - len(kept)


def _write_task(name: str, prompt: str, fire: datetime) -> None:
    task = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "prompt": prompt,
        "schedule": f"{fire.minute} {fire.hour} {fire.day} {fire.month} *",
        "notify_telegram": True,
        "sinks": ["voice", "telegram"],
        # Phrasing only — no tools needed (see scheduler._announce).
        "tools": False,
        "enabled": True,
        "created_at": datetime.now().isoformat(),
        "last_run": None,
    }
    with cs._sched_lock:
        tasks = cs._load_sched()
        tasks = [t for t in tasks if t.get("name") != name]
        tasks.append(task)
        cs._save_sched(tasks)


def apply_plan(decisions: list[dict], events: list[dict] | None = None) -> list[dict]:
    """Write one-time scheduler tasks for each decision. Returns what was scheduled."""
    now = datetime.now()
    scheduled = []
    events = upcoming() if events is None else events

    clear_planned({d["event"]["id"] for d in decisions}
                  | {e["id"] for e in events} | _planned_event_ids())

    # "It's time" notices: every timed event, independent of the planner. An
    # event nobody set a reminder on and the planner declined to preview still
    # has to tell you when it starts.
    if ANNOUNCE_AT_START:
        for ev in events:
            if ev["all_day"]:
                continue
            start = datetime.strptime(ev["start_at"], cs._FMT)
            if start <= now:
                continue
            _write_task(f"{START_PREFIX}{ev['id']}", start_announcement_prompt(ev), start)
            scheduled.append({"event": ev["title"], "at": start, "lead": 0,
                              "reason": "starting now"})

    for d in decisions:
        ev, lead = d["event"], d["lead_minutes"]
        start = datetime.strptime(ev["start_at"], cs._FMT)
        fire = cs._reminder_fire_dt(start, bool(ev["all_day"]), lead)
        # A heads-up whose moment has passed is noise, not information.
        if fire <= now:
            continue

        _write_task(f"{TASK_PREFIX}{ev['id']}_{lead}",
                    announcement_prompt(ev, lead, d["reason"], fire), fire)
        scheduled.append({"event": ev["title"], "at": fire, "lead": lead,
                          "reason": d["reason"]})
    return scheduled


def _planned_event_ids() -> set[int]:
    ids = set()
    for t in cs._load_sched():
        event_id = _event_id_from_task(t.get("name", ""))
        if event_id is not None:
            ids.add(event_id)
    return ids


async def plan_now() -> list[dict]:
    """One full planning pass. Safe to call any time."""
    events = upcoming()
    if not events:
        clear_planned()
        return []
    decisions = await decide(events)
    return apply_plan(decisions, events)


async def briefing_loop():
    """
    Re-plan whenever the upcoming schedule changes.

    Gated on a fingerprint rather than a timer: an unchanged day costs one
    SQLite read per tick, while adding an event gets a plan within a tick. A
    periodic forced re-plan keeps a stale plan from outliving its context.
    """
    print(f"  [briefing] Loop started (check {CHECK_SECONDS}s, window {WINDOW_HOURS}h)")
    last_print = None
    state = {"fingerprint": None, "planned_at": None}
    while True:
        try:
            events = upcoming()
            fp = fingerprint(events)
            age_ok = (state["planned_at"] is None or
                      (datetime.now() - state["planned_at"]).total_seconds()
                      > MAX_PLAN_AGE_HOURS * 3600)

            if fp != state["fingerprint"] or age_ok:
                scheduled = await plan_now()
                state["fingerprint"] = fp
                state["planned_at"] = datetime.now()
                summary = ", ".join(
                    f"{s['event']} at {s['at']:%H:%M}"
                    + ("" if s["lead"] == 0 else f" (-{s['lead']}m)")
                    for s in scheduled)
                if summary != last_print:
                    leads = sum(1 for s in scheduled if s["lead"])
                    starts = len(scheduled) - leads
                    print(f"  [briefing] Planned {starts} start notice(s) and "
                          f"{leads} heads-up(s)" + (f": {summary}" if summary else ""))
                    last_print = summary
        except Exception as e:
            print(f"  [briefing] loop error: {type(e).__name__}: {e}")
        await asyncio.sleep(CHECK_SECONDS)
