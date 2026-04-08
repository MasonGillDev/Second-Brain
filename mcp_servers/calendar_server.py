"""
Apple Calendar MCP Server.

Exposes macOS Calendar.app via AppleScript as MCP tools.
Runs as a local subprocess — communicates over stdin/stdout.

Uses parallel per-calendar queries to avoid the ~30s slowdown
from iterating all calendars in a single AppleScript call.
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("apple_calendar")


def run_applescript(script: str) -> str:
    """Run an AppleScript and return the output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def get_calendar_names() -> list[str]:
    """Get all calendar names."""
    raw = run_applescript('tell application "Calendar" to get name of every calendar')
    return [n.strip() for n in raw.split(",")]


def query_single_calendar(cal_name: str, start_str: str, end_str: str) -> str:
    """Query events from a single calendar."""
    script = f'''
tell application "Calendar"
    set startDate to date "{start_str}"
    set endDate to date "{end_str}"
    set output to ""
    set cal to calendar "{cal_name}"
    set evts to (every event of cal whose start date ≥ startDate and start date < endDate)
    repeat with evt in evts
        set evtStart to start date of evt
        set evtEnd to end date of evt
        set output to output & (summary of evt) & " | " & (evtStart as string) & " | " & (evtEnd as string) & " | " & "{cal_name}" & linefeed
    end repeat
    return output
end tell'''
    try:
        return run_applescript(script)
    except Exception:
        return ""


def query_all_calendars(start_str: str, end_str: str) -> str:
    """Query all calendars in parallel."""
    cal_names = get_calendar_names()
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(query_single_calendar, name, start_str, end_str): name
            for name in cal_names
        }
        for future in futures:
            result = future.result()
            if result:
                results.append(result)
    return "\n".join(results).strip()


@mcp.tool()
def list_calendars() -> str:
    """List all calendars available in Apple Calendar."""
    script = 'tell application "Calendar" to get name of every calendar'
    return run_applescript(script)


@mcp.tool()
def get_events(date: str = "", days: int = 1, calendar_name: str = "") -> str:
    """
    Get events from Apple Calendar.

    Args:
        date: Start date in YYYY-MM-DD format. Defaults to today.
        days: Number of days to look ahead (default 1 = just this day).
        calendar_name: Filter to a specific calendar. Empty = all calendars.
    """
    if date:
        try:
            start = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return f"Invalid date format: {date}. Use YYYY-MM-DD."
    else:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    end = start + timedelta(days=days)
    start_str = start.strftime("%B %d, %Y 12:00:00 AM")
    end_str = end.strftime("%B %d, %Y 12:00:00 AM")

    if calendar_name:
        result = query_single_calendar(calendar_name, start_str, end_str)
    else:
        result = query_all_calendars(start_str, end_str)

    if not result:
        date_label = date or "today"
        return f"No events found for {date_label} (+{days} day{'s' if days > 1 else ''})."
    return result


@mcp.tool()
def create_event(
    title: str,
    start_date: str,
    start_time: str = "",
    end_time: str = "",
    calendar_name: str = "Calendar",
    location: str = "",
    notes: str = "",
    all_day: bool = False,
) -> str:
    """
    Create a new event in Apple Calendar.

    Args:
        title: Event title/summary.
        start_date: Date in YYYY-MM-DD format.
        start_time: Start time in HH:MM format (24h). Ignored if all_day=True.
        end_time: End time in HH:MM format (24h). Ignored if all_day=True.
        calendar_name: Which calendar to add to (default "Calendar").
        location: Event location (optional).
        notes: Event notes/description (optional).
        all_day: If true, creates an all-day event.
    """
    try:
        dt = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        return f"Invalid date format: {start_date}. Use YYYY-MM-DD."

    if all_day:
        start_str = dt.strftime("%B %d, %Y 12:00:00 AM")
        end_dt = dt + timedelta(days=1)
        end_str = end_dt.strftime("%B %d, %Y 12:00:00 AM")
        allday_prop = "set allday event of newEvent to true"
    else:
        if not start_time or not end_time:
            return "start_time and end_time are required for non-all-day events. Use HH:MM format."
        try:
            st = datetime.strptime(start_time, "%H:%M")
            et = datetime.strptime(end_time, "%H:%M")
        except ValueError:
            return "Invalid time format. Use HH:MM (24-hour)."
        start_dt = dt.replace(hour=st.hour, minute=st.minute)
        end_dt = dt.replace(hour=et.hour, minute=et.minute)
        start_str = start_dt.strftime("%B %d, %Y %I:%M:%S %p")
        end_str = end_dt.strftime("%B %d, %Y %I:%M:%S %p")
        allday_prop = ""

    title_safe = title.replace('"', '\\"')
    location_safe = location.replace('"', '\\"')
    notes_safe = notes.replace('"', '\\"')

    location_prop = f'set location of newEvent to "{location_safe}"' if location else ""
    notes_prop = f'set description of newEvent to "{notes_safe}"' if notes else ""

    script = f'''
tell application "Calendar"
    set targetCal to calendar "{calendar_name}"
    set newEvent to make new event at end of events of targetCal with properties {{summary:"{title_safe}", start date:date "{start_str}", end date:date "{end_str}"}}
    {allday_prop}
    {location_prop}
    {notes_prop}
    return "Created: " & summary of newEvent & " on " & (start date of newEvent as string)
end tell'''

    return run_applescript(script)


@mcp.tool()
def search_events(query: str, days_ahead: int = 30) -> str:
    """
    Search for events by title across all calendars.

    Args:
        query: Text to search for in event titles.
        days_ahead: How many days ahead to search (default 30).
    """
    start = datetime.now().replace(hour=0, minute=0, second=0)
    end = start + timedelta(days=days_ahead)
    start_str = start.strftime("%B %d, %Y 12:00:00 AM")
    end_str = end.strftime("%B %d, %Y 12:00:00 AM")

    all_events = query_all_calendars(start_str, end_str)
    if not all_events:
        return f"No events matching '{query}' found in the next {days_ahead} days."

    # Filter by query client-side (faster than per-calendar AppleScript filtering)
    query_lower = query.lower()
    matched = []
    for line in all_events.split("\n"):
        if query_lower in line.lower():
            matched.append(line)

    if not matched:
        return f"No events matching '{query}' found in the next {days_ahead} days."
    return "\n".join(matched)


@mcp.tool()
def delete_event(title: str, date: str, calendar_name: str = "") -> str:
    """
    Delete an event by title and date.

    Args:
        title: Exact title of the event to delete.
        date: Date of the event in YYYY-MM-DD format.
        calendar_name: Calendar to delete from. If empty, searches all calendars.
    """
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return f"Invalid date format: {date}. Use YYYY-MM-DD."

    start_str = dt.strftime("%B %d, %Y 12:00:00 AM")
    end_dt = dt + timedelta(days=1)
    end_str = end_dt.strftime("%B %d, %Y 12:00:00 AM")
    title_safe = title.replace('"', '\\"')

    calendars_to_check = [calendar_name] if calendar_name else get_calendar_names()
    total_deleted = 0

    for cal in calendars_to_check:
        script = f'''
tell application "Calendar"
    set deleted to 0
    set cal to calendar "{cal}"
    set evts to (every event of cal whose summary is "{title_safe}" and start date ≥ date "{start_str}" and start date < date "{end_str}")
    repeat with evt in evts
        delete evt
        set deleted to deleted + 1
    end repeat
    return deleted
end tell'''
        try:
            result = run_applescript(script)
            total_deleted += int(result)
        except Exception:
            continue

    return f'Deleted {total_deleted} event(s) matching "{title}" on {date}.'


if __name__ == "__main__":
    mcp.run(transport="stdio")
