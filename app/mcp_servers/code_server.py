"""
Code MCP Server.

Delegates coding and system tasks to Claude Code (headless CLI).
Uses the user's Claude Code subscription — no API tokens consumed.

Three tools:
  - search_code: Search pre-indexed code knowledge (instant, free)
  - code_research: Read-only exploration (safe, no edits)
  - code_task: Can read, write, and edit files (scoped + capped)
"""

import sys
import os
import glob
import subprocess
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from memory.vector_store import VectorStore

_vector_store = VectorStore()

import signal
import atexit
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("code")

# Claude Code CLI path
CLAUDE_CLI = "/Users/masongill/.local/bin/claude"

# Track active subprocess so we can clean up on exit
_active_proc: subprocess.Popen | None = None


def _cleanup():
    """Kill any active Claude Code subprocess (and its children) on exit."""
    global _active_proc
    if _active_proc and _active_proc.poll() is None:
        print("  [code] Cleaning up active subprocess...", file=sys.stderr, flush=True)
        try:
            pgid = os.getpgid(_active_proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            _active_proc.terminate()
        try:
            _active_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(_active_proc.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                _active_proc.kill()
        _active_proc = None


atexit.register(_cleanup)
signal.signal(signal.SIGTERM, lambda *_: (_cleanup(), sys.exit(0)))
signal.signal(signal.SIGINT, lambda *_: (_cleanup(), sys.exit(0)))

# Session tracking: maps working_directory -> last session_id
_sessions: dict[str, str] = {}

# Safety defaults
DEFAULT_MAX_TURNS = 10
RESEARCH_MAX_TURNS = 50

# Read-only tools for research mode
RESEARCH_ALLOWED_TOOLS = [
    "Read",
    "Glob",
    "Grep",
    "Bash",
]

# Research mode blocks writes
RESEARCH_DISALLOWED_TOOLS = [
    "Write",
    "Edit",
    "Bash(rm:*)",
    "Bash(rm -rf:*)",
    "Bash(sudo:*)",
]

# Coding mode: full access with safety rails
CODING_ALLOWED_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
]

# Coding mode blocks destructive commands
CODING_DISALLOWED_TOOLS = [
    "Bash(rm -rf:*)",
    "Bash(sudo:*)",
    "Bash(wget:*)",
]


CLAUDE_PROJECTS_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects")


def _resolve_session_id(session_id: str) -> tuple[str, str | None]:
    """Resolve a possibly-short session id to the full UUID `claude --resume`
    needs. The hub/UI often shows only the 8-char prefix; accept a prefix and
    look up the matching transcript file in ~/.claude/projects.

    Returns (resolved_id, error). Empty input -> ("", None). On ambiguity or no
    match, returns ("", "[ERROR] ...") so the caller can surface it.
    """
    sid = (session_id or "").strip()
    if not sid:
        return "", None

    matches: set[str] = set()
    for proj in glob.glob(os.path.join(CLAUDE_PROJECTS_DIR, "*")):
        for f in glob.glob(os.path.join(proj, f"{sid}*.jsonl")):
            stem = os.path.basename(f)[: -len(".jsonl")]
            if stem == sid:
                return sid, None  # exact full-id match wins
            matches.add(stem)

    if len(matches) == 1:
        return next(iter(matches)), None
    if not matches:
        return "", f"[ERROR] No Claude Code session found matching id '{sid}'."
    return "", (
        f"[ERROR] Session id '{sid}' is ambiguous — it matches {len(matches)} "
        "sessions. Pass the full session id."
    )


def _run_claude(task: str, working_directory: str, allowed_tools: list[str],
                disallowed_tools: list[str] | None = None,
                max_turns: int = DEFAULT_MAX_TURNS,
                model: str = "sonnet",
                resume: bool = False,
                session_id: str = "") -> str:
    """Run Claude Code headless with streaming logs and return the result."""
    if not os.path.isdir(working_directory):
        return f"[ERROR] Directory does not exist: {working_directory}"

    # Don't let it touch the Second Brain repo
    sb_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    real_wd = os.path.realpath(working_directory)
    real_sb = os.path.realpath(sb_dir)
    if real_wd == real_sb or real_wd.startswith(real_sb + os.sep):
        return "[ERROR] Cannot run code tasks inside the Second Brain directory."

    cmd = [
        CLAUDE_CLI,
        "-p", task,
        "--output-format", "stream-json",
        "--verbose",
        "--max-turns", str(max_turns),
        "--model", model,
        "--allowed-tools", *allowed_tools,
    ]

    # Resume a session: an explicitly-passed session_id wins; otherwise fall
    # back to the last session we ran for this working directory.
    real_wd = os.path.realpath(working_directory)
    resume_id = session_id.strip()
    if not resume_id and resume and real_wd in _sessions:
        resume_id = _sessions[real_wd]
    if resume_id:
        # `claude --resume` requires the full UUID; accept a short prefix.
        resume_id, err = _resolve_session_id(resume_id)
        if err:
            return err
        cmd.extend(["--resume", resume_id])
        print(f"  [code] Resuming session {resume_id[:12]}...", file=sys.stderr, flush=True)

    if disallowed_tools:
        cmd.extend(["--disallowed-tools", *disallowed_tools])

    try:
        global _active_proc
        proc = subprocess.Popen(
            cmd,
            cwd=working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # own process group so cancel can kill children too
        )
        _active_proc = proc

        result_text = ""
        result_cost = 0
        result_turns = "?"
        signal_file = config.CANCEL_SIGNAL_FILE

        import selectors
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)

        idle_timeout = 240  # kill if no output for 2 minutes
        poll_interval = 0.5  # how often to re-check cancel signal / timeouts
        total_timeout = max_turns * 60  # rough cap based on turns
        start_time = time.time()
        last_output_time = time.time()

        while True:
            # Check for cancellation (polled every poll_interval seconds)
            if os.path.exists(signal_file):
                print("  [code] Cancellation signal received, terminating...", file=sys.stderr, flush=True)
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGTERM)
                except (ProcessLookupError, OSError):
                    proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        proc.kill()
                _active_proc = None
                return "[CANCELLED] Code task was cancelled by user."

            # Check total timeout
            elapsed = time.time() - start_time
            if elapsed > total_timeout:
                print(f"  [code] Total timeout ({total_timeout}s) exceeded, terminating...", file=sys.stderr, flush=True)
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                _active_proc = None
                partial = f"\n\n[Claude Code: timed out after {int(elapsed)}s]"
                return (result_text + partial) if result_text else "[ERROR] Claude Code timed out."

            # Wait for output, but wake up frequently to check the cancel signal
            ready = sel.select(timeout=poll_interval)
            if not ready:
                # No output yet — see if we've crossed the idle threshold
                if time.time() - last_output_time > idle_timeout:
                    print(f"  [code] No output for {idle_timeout}s, terminating...", file=sys.stderr, flush=True)
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    _active_proc = None
                    partial = f"\n\n[Claude Code: killed — no output for {idle_timeout}s]"
                    return (result_text + partial) if result_text else "[ERROR] Claude Code appears hung (no output)."
                continue

            line = proc.stdout.readline()
            if not line:
                break  # EOF — process finished
            last_output_time = time.time()

            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")

            # Log tool usage
            if event_type == "assistant" and "message" in event:
                msg = event["message"]
                for block in msg.get("content", []):
                    if block.get("type") == "tool_use":
                        tool_name = block.get("name", "?")
                        tool_input = str(block.get("input", ""))[:100]
                        print(f"  [code] {tool_name}({tool_input})", file=sys.stderr, flush=True)
                    elif block.get("type") == "text" and block.get("text"):
                        text_preview = block["text"][:120].replace("\n", " ")
                        print(f"  [code] thinking: {text_preview}", file=sys.stderr, flush=True)

            # Log tool results
            elif event_type == "tool" and "content" in event:
                for block in event.get("content", []):
                    if isinstance(block, dict) and block.get("text"):
                        preview = block["text"][:150].replace("\n", " ")
                        print(f"  [code] result: {preview}", file=sys.stderr, flush=True)

            # Capture final result and store session ID
            elif event_type == "result":
                result_text = event.get("result", "")
                result_cost = event.get("total_cost_usd", 0)
                result_turns = event.get("num_turns", "?")
                session_id = event.get("session_id", "")
                if session_id:
                    _sessions[real_wd] = session_id
                    print(f"  [code] Session saved: {session_id[:12]}... for {real_wd}", file=sys.stderr, flush=True)

        sel.close()
        proc.wait(timeout=10)
        _active_proc = None

        if not result_text:
            stderr = proc.stderr.read()
            return stderr.strip() or "[ERROR] No output from Claude Code."

        return f"{result_text}\n\n[Claude Code: {result_turns} turns, ${result_cost:.4f}]"

    except FileNotFoundError:
        return f"[ERROR] Claude CLI not found at {CLAUDE_CLI}."
    except Exception as e:
        _active_proc = None
        return f"[ERROR] Failed to run Claude Code: {e}"


@mcp.tool()
def search_code(query: str, top_k: int = 12) -> str:
    """
    Search pre-indexed codebase knowledge for classes, methods, and documentation.
    Try this once BEFORE using code_research — it's instant and free.

    Use for: understanding architecture, finding which services handle something,
    locating relevant files and classes, getting an overview before deep-diving.

    CRITICAL: Call search_code EXACTLY ONCE with a broad query.
    If you call it multiple times with different keywords, you're doing it wrong and wasting resources.
    This is vector search, not keyword guessing. One search, then move to code_research if needed. NO EXCEPTIONS."

    Args:
        query: Natural language description of what you're looking for.
        top_k: Maximum number of results to return (default 12).
    """
    if "code_context" not in _vector_store.collections:
        return "No code has been ingested yet. Run ingest_code first."

    results = _vector_store.query("code_context", query, top_k=top_k)
    results = [r for r in results if r.get("relevance", 0) >= config.RETRIEVAL_MIN_RELEVANCE_CODE]

    if not results:
        return "No relevant code context found."

    lines = []
    for r in results:
        fp = r.get("metadata", {}).get("file_path", "")
        line_num = r.get("metadata", {}).get("line_number", "")
        lines.append(f"- [{fp}:{line_num}] {r['text']}")

    return "\n".join(lines)


@mcp.tool()
def code_research(task: str, working_directory: str, resume: bool = True, session_id: str = "") -> str:
    """
    Research a codebase using Claude Code (read-only, safe).
    Use for: understanding code, finding patterns, exploring architecture,
    answering questions about a project, reading logs, checking git history.
    This tool does not work in /Users/masongill/Second Brain.


    This CANNOT modify any files. It can only read and search.

    Args:
        task: What to research or find out. Be specific.
        working_directory: Absolute path to the project directory.
        resume: If true, resume the last session for this project (default true).
        session_id: Pick up a specific existing Claude Code session by its id,
            continuing that conversation's context. Use this to resume one of the
            user's own sessions (e.g. an id from the claude_hub tools). Takes
            precedence over `resume`. Pass `working_directory` matching that
            session's cwd. Leave empty to start fresh / use the project's last session.
    """
    return _run_claude(
        task=task,
        working_directory=working_directory,
        allowed_tools=RESEARCH_ALLOWED_TOOLS,
        disallowed_tools=RESEARCH_DISALLOWED_TOOLS,
        max_turns=RESEARCH_MAX_TURNS,
        model="sonnet",
        resume=resume,
        session_id=session_id,
    )


@mcp.tool()
def code_task(task: str, working_directory: str, max_turns: int = DEFAULT_MAX_TURNS, resume: bool = True, session_id: str = "") -> str:
    """
    Delegate a coding task to Claude Code (can read, write, and edit files).
    Use for: writing code, fixing bugs, refactoring, creating files,
    running tests, installing packages, git operations.

    This CAN modify files in the specified directory. It cannot touch
    the Second Brain directory or run destructive system commands.
    This tool does not work in /Users/masongill/Second Brain.


    Args:
        task: What to build, fix, or do. Be specific about requirements.
        working_directory: Absolute path to the project directory.
        max_turns: Max agent loops (default 10, cap 25).
        resume: If true, resume the last session for this project (default true).
        session_id: Pick up a specific existing Claude Code session by its id,
            continuing that conversation's context. Use this to take over one of
            the user's own sessions (e.g. an id from the claude_hub tools). Takes
            precedence over `resume`. Pass `working_directory` matching that
            session's cwd. Leave empty to start fresh / use the project's last session.
    """
    max_turns = min(max_turns, 25)

    return _run_claude(
        task=task,
        working_directory=working_directory,
        allowed_tools=CODING_ALLOWED_TOOLS,
        disallowed_tools=CODING_DISALLOWED_TOOLS,
        max_turns=max_turns,
        model="sonnet",
        resume=resume,
        session_id=session_id,
    )


# ---- Background process management ----

_background_procs: dict[str, subprocess.Popen] = {}
_bg_counter = 0


@mcp.tool()
def run_background(command: str, working_directory: str, wait_seconds: int = 5) -> str:
    """
    Start a long-running process in the background (dev servers, watchers, etc.).
    Captures initial output for a few seconds then returns while the process keeps running.
    This tool does not work in /Users/masongill/Second Brain.

    Use stop_background to kill it later, or list_background to see what's running.

    Args:
        command: The shell command to run (e.g., "npm run dev", "python app.py").
        working_directory: Absolute path to run the command in.
        wait_seconds: How long to wait for startup output (default 5, max 30).
    """
    global _bg_counter

    if not os.path.isdir(working_directory):
        return f"[ERROR] Directory does not exist: {working_directory}"

    wait_seconds = min(max(wait_seconds, 2), 30)

    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,  # own process group so we can kill all children
        )

        # Capture startup output for a few seconds
        import selectors
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)

        output_lines = []
        deadline = time.time() + wait_seconds

        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            ready = sel.select(timeout=remaining)
            if ready:
                line = proc.stdout.readline()
                if not line:
                    break  # process exited
                output_lines.append(line.rstrip())
                print(f"  [bg] {line.rstrip()}", file=sys.stderr, flush=True)

        sel.close()

        # Check if it already died
        if proc.poll() is not None:
            remaining_output = proc.stdout.read()
            if remaining_output:
                output_lines.extend(remaining_output.strip().split("\n"))
            output = "\n".join(output_lines)
            return f"[ERROR] Process exited immediately (code {proc.returncode}):\n{output}"

        # Still running — register it
        _bg_counter += 1
        proc_id = f"bg_{_bg_counter}"
        _background_procs[proc_id] = proc

        output = "\n".join(output_lines) if output_lines else "(no output yet)"
        return f"Process started (id: {proc_id}, pid: {proc.pid}).\n\nStartup output:\n{output}"

    except Exception as e:
        return f"[ERROR] Failed to start process: {e}"


@mcp.tool()
def stop_background(process_id: str = "", stop_all: bool = False) -> str:
    """
    Stop a background process by its ID, or stop all background processes.

    Args:
        process_id: The process ID (e.g., "bg_1") from run_background.
        stop_all: If true, stop all background processes.
    """
    def _kill_proc_group(proc):
        """Kill a process and all its children via process group."""
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    if stop_all:
        if not _background_procs:
            return "No background processes running."
        results = []
        for pid, proc in list(_background_procs.items()):
            if proc.poll() is None:
                _kill_proc_group(proc)
                results.append(f"Stopped {pid}")
            else:
                results.append(f"{pid} already exited")
        _background_procs.clear()
        return "\n".join(results)

    if not process_id:
        return "[ERROR] Provide a process_id or set stop_all=true."

    proc = _background_procs.get(process_id)
    if not proc:
        available = ", ".join(_background_procs.keys()) or "none"
        return f"[ERROR] Unknown process '{process_id}'. Running: {available}"

    if proc.poll() is not None:
        del _background_procs[process_id]
        return f"{process_id} already exited (code {proc.returncode})."

    _kill_proc_group(proc)
    del _background_procs[process_id]
    return f"Stopped {process_id}."


@mcp.tool()
def list_background() -> str:
    """List all background processes and their status."""
    if not _background_procs:
        return "No background processes running."

    lines = []
    for proc_id, proc in list(_background_procs.items()):
        status = "running" if proc.poll() is None else f"exited ({proc.returncode})"
        lines.append(f"- {proc_id} (pid {proc.pid}): {status}")

        # Clean up dead processes
        if proc.poll() is not None:
            del _background_procs[proc_id]

    return "\n".join(lines)


# Clean up all background processes on exit
def _cleanup_background():
    for proc in _background_procs.values():
        if proc.poll() is None:
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGTERM)
                proc.wait(timeout=3)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass

atexit.register(_cleanup_background)


if __name__ == "__main__":
    mcp.run(transport="stdio")
