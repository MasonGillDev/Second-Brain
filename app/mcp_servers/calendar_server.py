"""
Internal Calendar MCP Server.

The agent's own calendar. Events live in SQLite (calendar_store) as the source
of truth — this replaces the old AppleScript bridge to macOS Calendar.app, which
gave better, tighter integration (custom fields, reminders, range queries) than
shelling out to Calendar.app.

Supports single-day and multi-day events (e.g. trips), timed or all-day, with a
title, time frame, location, and notes; reading a day, a week, or a date range;
and reminders that tie into the scheduler daemon.

All the heavy lifting lives in calendar_store.py; this server is a thin,
well-described wrapper that returns readable text.
"""

import sys
import os

# Add project root (app/) to path so we can import the shared store module.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

import calendar_store as store

mcp = FastMCP("calendar")


@mcp.tool()
def add_event(
    title: str,
    start_date: str,
    end_date: str = "",
    start_time: str = "",
    end_time: str = "",
    all_day: bool = False,
    location: str = "",
    notes: str = "",
    reminder_minutes: int = 0,
) -> str:
    """
    Add an event to the calendar. Handles single-day and multi-day events,
    timed or all-day.

      - Timed event:  give start_date + start_time (end_time optional).
      - All-day event: set all_day=true (or just omit start_time).
      - Multi-day event / trip: give end_date later than start_date — usually
        with all_day=true (e.g. a vacation Jul 5 → Jul 8).

    Args:
        title: Event title.
        start_date: Start day, YYYY-MM-DD.
        end_date: Last day for a multi-day event, YYYY-MM-DD. Omit for one day.
        start_time: Start time HH:MM (24h). Omit (or set all_day) for all-day.
        end_time: End time HH:MM (24h). Defaults to one hour after start_time.
        all_day: True for an all-day event (no clock time).
        location: Optional location.
        notes: Optional notes/description.
        reminder_minutes: Minutes before the event to be reminded (0 = no
            reminder). For all-day events the reminder counts back from 9:00 AM
            on the start date. Reminders are delivered via the scheduler.
    """
    try:
        ev = store.create_event(
            title=title, start_date=start_date, end_date=end_date,
            start_time=start_time, end_time=end_time, all_day=all_day,
            location=location, notes=notes, reminder_minutes=reminder_minutes,
        )
    except ValueError as e:
        return f"Could not add event: {e}"
    return "Added:\n" + store.format_event(ev) + store.reminder_status(ev)


@mcp.tool()
def get_day(date: str = "") -> str:
    """
    List events on a single day.

    Args:
        date: Day to read, YYYY-MM-DD. Defaults to today.
    """
    try:
        return store.day_view(date)
    except ValueError as e:
        return str(e)


@mcp.tool()
def get_week(date: str = "") -> str:
    """
    List events for the Monday–Sunday week containing a date.

    Args:
        date: Any day in the target week, YYYY-MM-DD. Defaults to this week.
    """
    try:
        return store.week_view(date)
    except ValueError as e:
        return str(e)


@mcp.tool()
def get_range(start_date: str, end_date: str) -> str:
    """
    List events overlapping an inclusive date range. Multi-day events that span
    into the range are included.

    Args:
        start_date: First day, YYYY-MM-DD.
        end_date: Last day, YYYY-MM-DD.
    """
    try:
        return store.range_view(start_date, end_date)
    except ValueError as e:
        return str(e)


@mcp.tool()
def get_event(event_id: int) -> str:
    """
    Get full details for one event by its id.

    Args:
        event_id: The event id (shown in brackets in listings, e.g. [12]).
    """
    ev = store.get_event(event_id)
    if not ev:
        return f"No event with id {event_id}."
    return store.format_event(ev) + store.reminder_status(ev)


@mcp.tool()
def update_event(
    event_id: int,
    title: str = "",
    start_date: str = "",
    end_date: str = "",
    start_time: str = "",
    end_time: str = "",
    all_day: bool | None = None,
    location: str = "",
    notes: str = "",
    reminder_minutes: int = -1,
) -> str:
    """
    Update an existing event. Only supplied fields change. If you change the
    date or time, the reminder (if any) is rescheduled automatically.

    Args:
        event_id: The event id to update.
        title: New title (omit to keep).
        start_date / end_date / start_time / end_time: New time frame pieces
            (omit any you don't want to change), YYYY-MM-DD / HH:MM.
        all_day: Set true/false to switch all-day vs timed; omit to keep.
        location: New location (omit to keep).
        notes: New notes (omit to keep).
        reminder_minutes: -1 = leave the reminder unchanged; 0 = remove the
            reminder; a positive number = remind that many minutes before.
    """
    kwargs: dict = {}
    if title:
        kwargs["title"] = title
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    if start_time:
        kwargs["start_time"] = start_time
    if end_time:
        kwargs["end_time"] = end_time
    if all_day is not None:
        kwargs["all_day"] = all_day
    if location:
        kwargs["location"] = location
    if notes:
        kwargs["notes"] = notes
    if reminder_minutes is not None and reminder_minutes >= 0:
        # 0 clears the reminder; >0 sets it (store maps 0 → None).
        kwargs["reminder_minutes"] = reminder_minutes

    if not kwargs:
        return "Nothing to update — supply at least one field to change."

    try:
        ev = store.update_event(event_id, **kwargs)
    except ValueError as e:
        return f"Could not update event: {e}"
    if not ev:
        return f"No event with id {event_id}."
    return "Updated:\n" + store.format_event(ev) + store.reminder_status(ev)


@mcp.tool()
def delete_event(event_id: int) -> str:
    """
    Delete an event by id (also cancels its reminder, if any).

    Args:
        event_id: The event id to delete.
    """
    ev = store.delete_event(event_id)
    if not ev:
        return f"No event with id {event_id}."
    return f'Deleted [{ev["id"]}] {ev["title"]}.'


if __name__ == "__main__":
    mcp.run(transport="stdio")
