"""
Dashboard Builder MCP Server.

Lets the agent create, update, list, delete, and restore
mini-dashboards in the AgentDashboards/ directory.

Uses Claude Code to actually build the dashboards — the agent
just describes what it wants.
"""

import sys
import os
import json
import shutil
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dashboards")

# Paths
BASE_DIR = Path(__file__).parent.parent
DASHBOARDS_DIR = BASE_DIR.parent / "clients" / "dashboards"
ARCHIVE_DIR = DASHBOARDS_DIR / ".archive"
CLAUDE_CLI = "/opt/homebrew/bin/claude"
DASHBOARD_SERVER_URL = "http://127.0.0.1:5001"

# Reuse code_server's subprocess management
_active_proc: subprocess.Popen | None = None

# Session tracking: maps working_directory -> last session_id
_sessions: dict[str, str] = {}


def _reload_dashboard_server():
    """Tell the main dashboard server to reload API blueprints."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{DASHBOARD_SERVER_URL}/api/dashboards/reload",
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        print("  [dashboard-builder] Reloaded dashboard server", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"  [dashboard-builder] Failed to reload server: {e}", file=sys.stderr, flush=True)


def _slugify(name: str) -> str:
    """Convert a name to a kebab-case slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def _run_claude(task: str, working_directory: str, max_turns: int = 15,
                resume: bool = True) -> str:
    """
    Run Claude Code headless in an isolated temp directory, then copy results back.
    This prevents Claude Code from walking up into the parent git repo.
    """
    if not os.path.isdir(working_directory):
        return f"[ERROR] Directory does not exist: {working_directory}"

    real_wd = os.path.realpath(working_directory)

    # Build in a temp directory outside the git repo so Claude Code
    # only sees the project files + CLAUDE.md, nothing else.
    import tempfile
    tmp_base = tempfile.mkdtemp(prefix="agent_dashboard_")
    tmp_project = os.path.join(tmp_base, os.path.basename(working_directory))

    try:
        # Copy existing project files into temp dir
        shutil.copytree(working_directory, tmp_project, dirs_exist_ok=True)

        # Copy CLAUDE.md into the temp project so Claude Code reads it
        claude_md = DASHBOARDS_DIR / "CLAUDE.md"
        if claude_md.exists():
            shutil.copy2(str(claude_md), tmp_project)

        cmd = [
            CLAUDE_CLI,
            "-p", task,
            "--output-format", "stream-json",
            "--verbose",
            "--max-turns", str(max_turns),
            "--model", "sonnet",
            "--allowed-tools", "Read", "Write", "Edit", "Glob", "Grep", "Bash",
            "--disallowed-tools", "Bash(rm -rf:*)", "Bash(sudo:*)",
            "--permission-mode", "bypassPermissions",
        ]

        # Don't resume sessions — temp dir paths won't match previous sessions,
        # and resumed sessions with -p can complete immediately.
        # Claude Code will just read the existing files fresh each time.

        global _active_proc
        proc = subprocess.Popen(
            cmd,
            cwd=tmp_project,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _active_proc = proc

        result_text = ""
        result_cost = 0
        result_turns = "?"

        import selectors
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)

        idle_timeout = 120
        total_timeout = max_turns * 60
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > total_timeout:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                _active_proc = None
                break

            ready = sel.select(timeout=idle_timeout)
            if not ready:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                _active_proc = None
                break

            line = proc.stdout.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")

            if event_type == "assistant" and "message" in event:
                for block in event["message"].get("content", []):
                    if block.get("type") == "tool_use":
                        tool_name = block.get("name", "?")
                        print(f"  [dashboard-builder] {tool_name}", file=sys.stderr, flush=True)

            elif event_type == "result":
                result_text = event.get("result", "")
                result_cost = event.get("total_cost_usd", 0)
                result_turns = event.get("num_turns", "?")
                session_id = event.get("session_id", "")
                if session_id:
                    _sessions[real_wd] = session_id
                    print(f"  [dashboard-builder] Session saved: {session_id[:12]}... for {real_wd}",
                          file=sys.stderr, flush=True)

        sel.close()
        proc.wait(timeout=10)
        _active_proc = None

        # Copy results back from temp dir to the real project directory,
        # excluding CLAUDE.md (that's our convention file, not a project file)
        for item in os.listdir(tmp_project):
            if item == "CLAUDE.md":
                continue
            src = os.path.join(tmp_project, item)
            dst = os.path.join(working_directory, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

        if not result_text:
            stderr = proc.stderr.read()
            return stderr.strip() or "[ERROR] No output from Claude Code."

        return f"{result_text}\n\n[Claude Code: {result_turns} turns, ${result_cost:.4f}]"

    except FileNotFoundError:
        return f"[ERROR] Claude CLI not found at {CLAUDE_CLI}."
    except Exception as e:
        _active_proc = None
        return f"[ERROR] Failed to run Claude Code: {e}"
    finally:
        # Clean up temp directory
        shutil.rmtree(tmp_base, ignore_errors=True)


@mcp.tool()
def create_dashboard(name: str, requirements: str, max_turns: int = 15) -> str:
    """
    Create a new mini-dashboard. Claude Code builds it based on your requirements.
    The CLAUDE.md in AgentDashboards/ defines the conventions automatically.

    Args:
        name: Human-readable name (e.g., "Habit Tracker"). Will be slugified for the directory.
        requirements: Detailed description of what the dashboard should do, look like, and any features.
        max_turns: Max Claude Code agent loops (default 15, cap 25).
    """
    slug = _slugify(name)
    if not slug:
        return "[ERROR] Invalid name — couldn't generate a slug."

    project_dir = DASHBOARDS_DIR / slug
    if project_dir.exists():
        return f"[ERROR] Dashboard '{slug}' already exists. Use update_dashboard to modify it."

    # Check if archived version exists
    archived = ARCHIVE_DIR / slug
    if archived.exists():
        return f"[ERROR] An archived dashboard '{slug}' exists. Restore it first or choose a different name."

    # Create the directory structure
    project_dir.mkdir(parents=True)
    (project_dir / "static").mkdir()

    # Write manifest
    manifest = {
        "name": name,
        "description": requirements[:200],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (project_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    max_turns = min(max_turns, 25)

    task = f"""Build a dashboard called "{name}".

Requirements:
{requirements}

The CLAUDE.md in the parent directory (AgentDashboards/) describes the conventions.
Read it first, then build the dashboard in this directory.

This directory already has:
- manifest.json (already created, don't modify)
- static/ (put index.html and assets here)

Create api.py and data.json only if the dashboard needs server-side persistence.
"""

    result = _run_claude(task, str(project_dir), max_turns=max_turns, resume=False)

    # Verify index.html was created
    if not (project_dir / "static" / "index.html").exists():
        return f"[WARNING] Claude Code finished but no index.html was created.\n\n{result}"

    _reload_dashboard_server()
    return f"Dashboard '{name}' created at /d/{slug}/\n\n{result}"


@mcp.tool()
def update_dashboard(slug: str, instructions: str, max_turns: int = 15) -> str:
    """
    Update an existing dashboard. Claude Code modifies it based on your instructions.

    Args:
        slug: The dashboard slug (directory name, e.g., "habit-tracker").
        instructions: What to change, add, or fix.
        max_turns: Max Claude Code agent loops (default 15, cap 25).
    """
    project_dir = DASHBOARDS_DIR / slug
    if not project_dir.exists() or not (project_dir / "manifest.json").exists():
        return f"[ERROR] Dashboard '{slug}' not found."

    max_turns = min(max_turns, 25)

    task = f"""Update this existing dashboard.

Instructions:
{instructions}

The CLAUDE.md in the parent directory (AgentDashboards/) describes the conventions.
Read the existing code first, then make the requested changes.
"""

    result = _run_claude(task, str(project_dir), max_turns=max_turns)
    _reload_dashboard_server()
    return f"Dashboard '{slug}' updated.\n\n{result}"


@mcp.tool()
def list_dashboards() -> str:
    """List all active and archived dashboards."""
    lines = []

    # Active
    active = []
    if DASHBOARDS_DIR.exists():
        for d in sorted(DASHBOARDS_DIR.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            manifest_path = d / "manifest.json"
            if manifest_path.exists():
                try:
                    m = json.loads(manifest_path.read_text())
                    has_api = "+" if (d / "api.py").exists() else "-"
                    active.append(f"  [{d.name}] {m.get('name', d.name)} — {m.get('description', 'No description')[:80]}  (api:{has_api})")
                except (json.JSONDecodeError, OSError):
                    active.append(f"  [{d.name}] (corrupt manifest)")

    if active:
        lines.append("Active dashboards:")
        lines.extend(active)
    else:
        lines.append("No active dashboards.")

    # Archived
    archived = []
    if ARCHIVE_DIR.exists():
        for d in sorted(ARCHIVE_DIR.iterdir()):
            if not d.is_dir():
                continue
            manifest_path = d / "manifest.json"
            if manifest_path.exists():
                try:
                    m = json.loads(manifest_path.read_text())
                    archived.append(f"  [{d.name}] {m.get('name', d.name)}")
                except (json.JSONDecodeError, OSError):
                    archived.append(f"  [{d.name}] (corrupt manifest)")

    if archived:
        lines.append("\nArchived dashboards:")
        lines.extend(archived)

    return "\n".join(lines)


@mcp.tool()
def delete_dashboard(slug: str) -> str:
    """
    Archive (soft-delete) a dashboard. It can be restored later.

    Args:
        slug: The dashboard slug (directory name).
    """
    src = DASHBOARDS_DIR / slug
    if not src.exists() or not (src / "manifest.json").exists():
        return f"[ERROR] Dashboard '{slug}' not found."

    ARCHIVE_DIR.mkdir(exist_ok=True)
    dest = ARCHIVE_DIR / slug
    if dest.exists():
        shutil.rmtree(str(dest))
    shutil.move(str(src), str(dest))

    return f"Dashboard '{slug}' archived. Use restore_dashboard to bring it back."


@mcp.tool()
def restore_dashboard(slug: str) -> str:
    """
    Restore an archived dashboard.

    Args:
        slug: The dashboard slug (directory name).
    """
    src = ARCHIVE_DIR / slug
    if not src.exists():
        return f"[ERROR] No archived dashboard '{slug}' found."

    dest = DASHBOARDS_DIR / slug
    if dest.exists():
        return f"[ERROR] An active dashboard '{slug}' already exists."

    shutil.move(str(src), str(dest))
    return f"Dashboard '{slug}' restored. Available at /d/{slug}/"


if __name__ == "__main__":
    mcp.run(transport="stdio")
