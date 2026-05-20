"""
Claude Hub MCP Server.

Gives the agent tools to observe and act on its Claude Code sessions through
the Claude Hub web app (a Next.js dashboard over ~/.claude). Talks to the Hub's
REST API over HTTP — the Hub owns all the logic (transcript parsing, name
resolution, terminal control), so this server is a thin, well-described client.

Capability tiers exposed (no destructive tools by design):
  - Read:            list_projects, list_sessions, get_session, check_attention
  - Safe writes:     set_session_status, rename_session, clear_attention
  - Terminal driving: resume_session, start_session

Requires the Hub to be running (e.g. `next dev` on :3000). Set CLAUDE_HUB_URL
to point elsewhere.
"""

import os
from datetime import datetime, timezone

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("claude_hub")

BASE_URL = os.environ.get("CLAUDE_HUB_URL", "http://localhost:3000").rstrip("/")
TIMEOUT = 10.0  # generous: resume/start spawn Terminal.app via AppleScript


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

class HubError(Exception):
    """A user-facing error to surface back to the agent as a tool result."""


def _request(method: str, path: str, json: dict | None = None) -> dict:
    """Call the Hub API, returning parsed JSON or raising HubError with a
    message the agent can relay to the user."""
    url = f"{BASE_URL}{path}"
    try:
        resp = httpx.request(method, url, json=json, timeout=TIMEOUT)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise HubError(
            f"Claude Hub isn't reachable at {BASE_URL}. "
            "Is the app running (e.g. `next dev`)?"
        )
    except httpx.HTTPError as e:
        raise HubError(f"Request to Claude Hub failed: {e}")

    try:
        data = resp.json()
    except ValueError:
        raise HubError(f"Claude Hub returned a non-JSON response (HTTP {resp.status_code}).")

    if resp.status_code >= 400:
        detail = data.get("error") or data.get("detail") or resp.text
        raise HubError(f"Claude Hub error (HTTP {resp.status_code}): {detail}")
    return data


def _rel_time(iso: str | None) -> str:
    """Compact 'how long ago' for an ISO timestamp."""
    if not iso:
        return "unknown"
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    now = datetime.now(timezone.utc)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    secs = (now - then).total_seconds()
    if secs < 45:
        return "just now"
    mins = secs / 60
    if mins < 60:
        return f"{round(mins)}m ago"
    hrs = mins / 60
    if hrs < 24:
        return f"{round(hrs)}h ago"
    days = hrs / 24
    if days < 7:
        return f"{round(days)}d ago"
    return f"{round(days / 7)}w ago"


def _badges(session: dict) -> str:
    """Inline status badges for a session summary."""
    out = []
    if session.get("running"):
        out.append("● running")
    att = session.get("attention")
    if att:
        out.append(f"⚠ {att.get('event')}")
    status = session.get("status")
    if status:
        out.append(f"[{status}]")
    return " ".join(out)


def _fmt_session_line(s: dict) -> str:
    """One-block summary of a session for list views.

    The full session id is shown (not truncated) because callers pass it to
    `claude --resume`, which requires the complete UUID.
    """
    badges = _badges(s)
    head = f"- {s.get('name', '?')}"
    if badges:
        head += f"  {badges}"
    parts = [head, f"  id: {s['id']}"]
    meta = []
    if s.get("messageCount") is not None:
        meta.append(f"{s['messageCount']} msgs")
    if s.get("gitBranch"):
        meta.append(f"branch {s['gitBranch']}")
    meta.append(_rel_time(s.get("lastActivity")))
    parts.append("  " + " · ".join(meta))
    if s.get("lastPrompt"):
        parts.append(f"  last prompt: {s['lastPrompt']}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_projects() -> str:
    """
    List all Claude Code projects tracked by the Hub, most recently active first.

    Each project corresponds to a working directory you've run Claude Code in.
    Shows how many sessions it has, how many are currently running, and how many
    are waiting on the user (attention). Use the project id with list_sessions.
    """
    data = _request("GET", "/api/projects")
    projects = data.get("projects", [])
    if not projects:
        return "No projects found."

    lines = []
    for p in projects:
        flags = []
        if p.get("runningCount"):
            flags.append(f"● {p['runningCount']} running")
        if p.get("attentionCount"):
            flags.append(f"⚠ {p['attentionCount']} need input")
        flag_str = f"  ({', '.join(flags)})" if flags else ""
        lines.append(
            f"- {p.get('name', '?')}{flag_str}\n"
            f"  id: {p['id']}\n"
            f"  path: {p.get('path', '?')}\n"
            f"  {p.get('sessionCount', 0)} sessions · active {_rel_time(p.get('lastActivity'))}"
        )
    return "\n\n".join(lines)


@mcp.tool()
def list_sessions(project_id: str) -> str:
    """
    List the Claude Code sessions inside a project, most recently active first.

    Args:
        project_id: The project's id from list_projects (e.g. "-Users-you-myrepo").
    """
    data = _request("GET", f"/api/projects/{project_id}/sessions")
    sessions = data.get("sessions", [])
    project = data.get("project", {})
    if not sessions:
        return f"No sessions in project '{project.get('name', project_id)}'."

    header = f"Sessions in {project.get('name', project_id)} ({len(sessions)}):\n"
    return header + "\n".join(_fmt_session_line(s) for s in sessions)


@mcp.tool()
def get_session(session_id: str) -> str:
    """
    Get full detail for one Claude Code session: model, message count, git branch,
    working directory, current status/attention, and the most recent user and
    assistant turns. Use this to understand what a session is doing or waiting on.

    Args:
        session_id: The session id (full uuid, or the short 8-char prefix shown in lists).
    """
    s = _request("GET", f"/api/sessions/{session_id}").get("session", {})
    badges = _badges(s)
    lines = [
        f"{s.get('name', '?')}  {badges}".rstrip(),
        f"id: {s['id']}",
        f"project: {s.get('projectId')}",
        f"cwd: {s.get('cwd') or '?'}",
        f"branch: {s.get('gitBranch') or '?'}  ·  model: {s.get('model') or '?'}",
        f"messages: {s.get('messageCount', 0)}  ·  last active {_rel_time(s.get('lastActivity'))}",
    ]
    att = s.get("attention")
    if att:
        msg = f" — {att['message']}" if att.get("message") else ""
        lines.append(f"attention: {att.get('event')}{msg} ({_rel_time(att.get('at'))})")
    last_user = s.get("lastUser")
    if last_user and last_user.get("text"):
        lines.append(f"\nlast user: {last_user['text'][:500]}")
    last_asst = s.get("lastAssistant")
    if last_asst:
        text = (last_asst.get("text") or "").strip()
        tools = last_asst.get("tools") or []
        tail = f"[tools: {', '.join(tools)}]" if tools else ""
        lines.append(f"\nlast assistant: {text[:500]} {tail}".rstrip())
    return "\n".join(lines)


@mcp.tool()
def check_attention() -> str:
    """
    Check which Claude Code sessions need the user's attention right now, and
    which are actively running (busy). This reflects live hook events from
    Claude Code (a session finished, hit a notification, or a subagent stopped).

    Use this to answer "is any Claude session waiting on me?" A running session
    is never also waiting — running always wins.
    """
    data = _request("GET", "/api/events")
    attention = data.get("attention", {}) or {}
    running = data.get("running", []) or []

    lines = []
    if attention:
        lines.append(f"⚠ {len(attention)} session(s) need attention:")
        for sid, entry in attention.items():
            cwd = entry.get("cwd") or "?"
            msg = f" — {entry['message']}" if entry.get("message") else ""
            lines.append(
                f"  - {entry.get('event')}{msg}\n"
                f"    id: {sid}\n"
                f"    in {cwd} ({_rel_time(entry.get('at'))})"
            )
    else:
        lines.append("No sessions are waiting on you.")

    if running:
        lines.append(f"\n● {len(running)} session(s) currently running:")
        lines.extend(f"  - {sid}" for sid in running)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Safe-write tools (only touch the Hub's own sidecar, never Claude's state)
# ---------------------------------------------------------------------------

@mcp.tool()
def set_session_status(session_id: str, status: str) -> str:
    """
    Set the user-facing lifecycle flag on a session.

    Args:
        session_id: The session id.
        status: One of:
            "open"     — flagged as having more work to do.
            "finished" — flagged as wrapped up / in a good state.
            "clear"    — remove any flag.
    """
    if status not in ("open", "finished", "clear"):
        return "status must be 'open', 'finished', or 'clear'."
    payload_status = None if status == "clear" else status
    s = _request("PATCH", f"/api/sessions/{session_id}", json={"status": payload_status}).get("session", {})
    return f"Set status of '{s.get('name', session_id)}' to {payload_status or 'none'}."


@mcp.tool()
def rename_session(session_id: str, name: str) -> str:
    """
    Give a session a custom display name in the Hub. This is stored in the Hub's
    own sidecar and does not change Claude Code's session state. Pass an empty
    string to clear the custom name (falls back to the auto-resolved name).

    Args:
        session_id: The session id.
        name: The new display name (empty string to clear).
    """
    s = _request("PATCH", f"/api/sessions/{session_id}", json={"name": name}).get("session", {})
    return f"Renamed session to '{s.get('name', name)}' (source: {s.get('nameSource')})."


@mcp.tool()
def clear_attention(session_id: str = "") -> str:
    """
    Dismiss attention flags so a session no longer shows as waiting.

    Args:
        session_id: The session to clear. Pass an empty string to clear ALL
                    pending attention at once.
    """
    if session_id:
        _request("DELETE", f"/api/events/{session_id}")
        return f"Cleared attention for session {session_id[:8]}."
    _request("DELETE", "/api/events")
    return "Cleared all pending attention."


# ---------------------------------------------------------------------------
# Terminal-driving tools (open/focus real Terminal.app windows)
# ---------------------------------------------------------------------------

@mcp.tool()
def resume_session(session_id: str) -> str:
    """
    Resume a Claude Code session. If its terminal window is still open, that tab
    is brought to the front; otherwise a new Terminal.app window opens running
    `claude --resume`. Use this to hand a waiting session back to the user.

    Args:
        session_id: The session id to resume.
    """
    data = _request("POST", f"/api/sessions/{session_id}/resume")
    action = data.get("action", "resumed")
    verb = "Focused existing terminal for" if action == "focused" else "Opened a terminal resuming"
    return f"{verb} session {session_id[:8]} in {data.get('cwd', '?')}."


@mcp.tool()
def start_session(path: str, name: str = "") -> str:
    """
    Start a brand-new Claude Code session by opening a Terminal.app window in a
    directory and launching `claude` there.

    Args:
        path: Absolute directory path to start the session in (e.g. "/Users/you/repo").
              The directory must already exist. "~" is expanded by the Hub.
        name: Optional name to give the new session (`claude -n <name>`).
    """
    payload: dict = {"path": path}
    if name:
        payload["name"] = name
    data = _request("POST", "/api/projects", json=payload)
    return f"Started a new Claude session in {data.get('cwd', path)}."


if __name__ == "__main__":
    mcp.run(transport="stdio")
