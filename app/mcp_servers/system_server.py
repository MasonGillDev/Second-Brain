"""
System Admin MCP Server.

Delegates system administration of the user's Mac to Claude Code (headless CLI),
the same way the `code` tools delegate coding. Uses the user's Claude Code
subscription — no API tokens consumed.

ONE tool: system_admin(request, session_id, approve).

Design (matches what the user asked for):
  - Runs Claude Code in AUTO mode (no interactive prompts) but READ-MOSTLY: it
    investigates freely and must STOP and ask before changing anything.
  - "Stop and ask" is enforced two ways: (1) an --append-system-prompt protocol
    that makes Claude emit a `CONFIRMATION REQUIRED:` block and end its turn, and
    (2) a hard permission boundary — in the default (un-approved) turn, Write/Edit
    and all obviously-mutating shell commands are disallowed, so even if the model
    ignores the prompt it physically cannot change the system.
  - RESUMABLE: every turn returns its Claude Code session id. After the user
    approves, the Second Brain agent calls this tool again with that session_id
    and approve=true, which RESUMES the same session with write access unlocked so
    the admin can carry out exactly the approved steps.

Built on top of the `code` tool set (same streaming/cancel/watchdog machinery as
app/mcp_servers/code_server.py) but kept self-contained so changes here can never
regress the proven code tools.
"""

import sys
import os
import glob
import subprocess
import json
import time
import signal
import atexit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("system")

# Claude Code CLI path (same binary the code tools use).
CLAUDE_CLI = "/Users/masongill/.local/bin/claude"

# Where the admin starts. Home dir so it can see the whole machine; NOT the
# Second Brain repo (it must never rewrite its own brain — see the guard below).
DEFAULT_WORKDIR = os.path.expanduser("~")

# Grant the structured file tools (Read/Glob/Grep/Edit/Write) access to the whole
# filesystem; Bash already reaches anywhere. Writes stay gated by `approve`.
ADD_DIRS = ["/"]

MODEL = "sonnet"
DEFAULT_MAX_TURNS = 30
MAX_TURNS_CAP = 60
IDLE_TIMEOUT = 300          # kill if no output for 5 minutes (installs print progress)

CLAUDE_PROJECTS_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects")

# --- Permission profiles -----------------------------------------------------

# Truly catastrophic commands — NEVER allowed, in any mode, even after approval.
# This is a backstop, not a sandbox: pattern matching can't catch every variant
# (e.g. shell redirects), so the real safety is read-mostly + the approval gate.
CATASTROPHIC_DISALLOWED = [
    "Bash(rm -rf /:*)",
    "Bash(rm -rf /*)",
    "Bash(rm -fr /:*)",
    "Bash(sudo rm -rf /:*)",
    "Bash(mkfs:*)",
    "Bash(dd:*)",
    "Bash(diskutil eraseDisk:*)",
    "Bash(diskutil eraseVolume:*)",
    "Bash(diskutil reformat:*)",
    "Bash(diskutil zeroDisk:*)",
    "Bash(diskutil apfs deleteContainer:*)",
]

# Investigate mode: read-only. Allow read tools + Bash, but block Write/Edit and
# every obviously-mutating command so the un-approved turn cannot change anything.
INVESTIGATE_ALLOWED = ["Read", "Glob", "Grep", "Bash"]
INVESTIGATE_DISALLOWED = CATASTROPHIC_DISALLOWED + [
    "Write", "Edit", "NotebookEdit",
    "Bash(sudo:*)",
    "Bash(rm:*)", "Bash(rmdir:*)", "Bash(unlink:*)", "Bash(shred:*)",
    "Bash(mv:*)", "Bash(cp:*)", "Bash(ln:*)",
    "Bash(touch:*)", "Bash(mkdir:*)", "Bash(tee:*)", "Bash(install:*)",
    "Bash(chmod:*)", "Bash(chown:*)", "Bash(chflags:*)", "Bash(xattr:*)",
    "Bash(kill:*)", "Bash(killall:*)", "Bash(pkill:*)",
    "Bash(launchctl:*)", "Bash(systemsetup:*)", "Bash(scutil:*)",
    "Bash(defaults write:*)", "Bash(defaults delete:*)", "Bash(pmset:*)",
    "Bash(brew install:*)", "Bash(brew uninstall:*)", "Bash(brew upgrade:*)",
    "Bash(brew reinstall:*)", "Bash(brew cleanup:*)", "Bash(brew remove:*)",
    "Bash(npm install:*)", "Bash(npm uninstall:*)", "Bash(npm i:*)",
    "Bash(pip install:*)", "Bash(pip3 install:*)", "Bash(pipx install:*)",
    "Bash(gem install:*)", "Bash(cargo install:*)", "Bash(go install:*)",
    "Bash(softwareupdate:*)", "Bash(mas install:*)",
    "Bash(git push:*)", "Bash(git commit:*)", "Bash(git reset:*)",
    "Bash(git checkout:*)", "Bash(git clean:*)", "Bash(git rebase:*)",
    "Bash(git merge:*)", "Bash(git restore:*)",
    "Bash(networksetup:*)", "Bash(ifconfig:*)", "Bash(pfctl:*)", "Bash(dscl:*)",
    "Bash(apachectl:*)", "Bash(nginx:*)", "Bash(crontab:*)",
]

# Execute mode (resumed after explicit approval): write access unlocked. Only the
# catastrophic backstop remains. The append-system-prompt still tells the admin to
# stop again if anything beyond the approved scope turns out to be destructive.
EXECUTE_ALLOWED = ["Read", "Glob", "Grep", "Bash", "Write", "Edit"]
EXECUTE_DISALLOWED = list(CATASTROPHIC_DISALLOWED)

_SB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Append-system-prompts (the "stop and ask" protocol) ---------------------

_CONFIRM_BLOCK_SPEC = (
    "CONFIRMATION REQUIRED:\n"
    "- What I want to do: <plain-language summary>\n"
    "- Exact command(s)/change(s): <the literal commands or file edits>\n"
    "- Why: <reason it's needed>\n"
    "- Risk / reversibility: <impact, and whether it can be undone>"
)

INVESTIGATE_PROMPT = (
    "You are the SYSTEM ADMINISTRATOR for this Mac, invoked headlessly by the "
    "user's Second Brain assistant to act on their behalf. You are in READ-MOSTLY "
    "mode.\n\n"
    "You MAY freely: read files and logs, list processes, inspect disk/network/"
    "service status, run any read-only diagnostic command, and explain findings.\n\n"
    "You MUST NOT, in this mode, take ANY action that changes the system. That "
    "includes (non-exhaustive): writing/editing/creating/moving/deleting files, "
    "installing/uninstalling/upgrading software, starting/stopping/restarting "
    "services, killing processes, changing permissions or ownership, editing "
    "configuration, changing network/firewall settings, or anything needing sudo.\n\n"
    "When the request requires such a change, do NOT attempt it. Instead:\n"
    "1. Investigate enough to know EXACTLY what you would do.\n"
    "2. End your reply with this block, verbatim format:\n\n"
    f"{_CONFIRM_BLOCK_SPEC}\n\n"
    "Then STOP and end your turn — run nothing else. You will be re-invoked with "
    "the user's decision; only if approved will you be permitted to carry out "
    "exactly those steps. If several distinct changes are needed, list them all in "
    "one block so the user can approve the whole plan at once.\n\n"
    f"Never modify the Second Brain application at {_SB_DIR}. Keep any proposed "
    "changes minimal and reversible. If the request is ambiguous or risky, ask "
    "instead of guessing."
)

EXECUTE_PROMPT = (
    "You are the SYSTEM ADMINISTRATOR for this Mac, RESUMED after the user "
    "APPROVED the action you proposed. You now have permission to carry out the "
    "specific change(s) from your previous CONFIRMATION REQUIRED block — and only "
    "those.\n\n"
    "Carry them out now, then report concisely what you did and the outcome "
    "(including any command output that matters).\n\n"
    "If, while doing this, you find that ADDITIONAL changes beyond what was "
    "approved are needed, or anything unexpected or destructive arises, STOP and "
    "emit a NEW CONFIRMATION REQUIRED block instead of proceeding — never expand "
    "scope without asking again.\n\n"
    f"Still never touch the Second Brain application at {_SB_DIR}, and never run "
    "whole-disk erase/format, rm -rf of system roots, or fork bombs even if they "
    "seem implied."
)

# --- Subprocess tracking / cleanup (own instance; independent of code_server) -

_active_proc: subprocess.Popen | None = None


def _cleanup():
    global _active_proc
    if _active_proc and _active_proc.poll() is None:
        print("  [system] Cleaning up active subprocess...", file=sys.stderr, flush=True)
        try:
            os.killpg(os.getpgid(_active_proc.pid), signal.SIGTERM)
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


def _resolve_session_id(session_id: str) -> tuple[str, str | None]:
    """Resolve a possibly-short session id to the full UUID `claude --resume`
    needs. Returns (resolved_id, error). Empty input -> ("", None)."""
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


def _run_admin(request: str, approve: bool, session_id: str, max_turns: int) -> dict:
    """Run Claude Code headless for a system-admin turn. Returns a dict:
    {text, session_id, turns, cost, status, error}. status in
    {DONE, AWAITING_CONFIRMATION, CANCELLED, ERROR}."""
    workdir = DEFAULT_WORKDIR
    if not os.path.isdir(workdir):
        return {"error": f"[ERROR] Working directory does not exist: {workdir}", "status": "ERROR"}

    # Self-protection: never operate from inside the Second Brain repo.
    real_wd = os.path.realpath(workdir)
    real_sb = os.path.realpath(_SB_DIR)
    if real_wd == real_sb or real_wd.startswith(real_sb + os.sep):
        return {"error": "[ERROR] System admin cannot run inside the Second Brain directory.", "status": "ERROR"}

    if approve:
        allowed, disallowed, sys_prompt = EXECUTE_ALLOWED, EXECUTE_DISALLOWED, EXECUTE_PROMPT
    else:
        allowed, disallowed, sys_prompt = INVESTIGATE_ALLOWED, INVESTIGATE_DISALLOWED, INVESTIGATE_PROMPT

    cmd = [
        CLAUDE_CLI,
        "-p", request,
        "--output-format", "stream-json",
        "--verbose",
        "--max-turns", str(max_turns),
        "--model", MODEL,
        "--append-system-prompt", sys_prompt,
        "--allowed-tools", *allowed,
        "--disallowed-tools", *disallowed,
    ]
    for d in ADD_DIRS:
        cmd.extend(["--add-dir", d])

    # Resume an existing admin session if asked. Required when approving.
    resume_id = (session_id or "").strip()
    if resume_id:
        resume_id, err = _resolve_session_id(resume_id)
        if err:
            return {"error": err, "status": "ERROR"}
        cmd.extend(["--resume", resume_id])
        print(f"  [system] Resuming session {resume_id[:12]}... (approve={approve})", file=sys.stderr, flush=True)

    try:
        global _active_proc
        proc = subprocess.Popen(
            cmd, cwd=workdir,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,  # own process group so cancel kills children too
        )
        _active_proc = proc

        result_text = ""
        result_cost = 0
        result_turns = "?"
        out_session_id = resume_id or ""
        signal_file = config.CANCEL_SIGNAL_FILE

        import selectors
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)

        poll_interval = 0.5
        total_timeout = max_turns * 60
        start_time = time.time()
        last_output_time = time.time()

        def _terminate():
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    proc.kill()

        while True:
            if os.path.exists(signal_file):
                print("  [system] Cancellation signal received, terminating...", file=sys.stderr, flush=True)
                _terminate()
                _active_proc = None
                return {"status": "CANCELLED", "session_id": out_session_id}

            elapsed = time.time() - start_time
            if elapsed > total_timeout:
                print(f"  [system] Total timeout ({total_timeout}s) exceeded, terminating...", file=sys.stderr, flush=True)
                _terminate()
                _active_proc = None
                partial = f"\n\n[system admin: timed out after {int(elapsed)}s]"
                return {"text": (result_text + partial) if result_text else "",
                        "error": None if result_text else "[ERROR] System admin timed out.",
                        "session_id": out_session_id, "status": "DONE" if result_text else "ERROR"}

            ready = sel.select(timeout=poll_interval)
            if not ready:
                if time.time() - last_output_time > IDLE_TIMEOUT:
                    print(f"  [system] No output for {IDLE_TIMEOUT}s, terminating...", file=sys.stderr, flush=True)
                    _terminate()
                    _active_proc = None
                    partial = f"\n\n[system admin: killed — no output for {IDLE_TIMEOUT}s]"
                    return {"text": (result_text + partial) if result_text else "",
                            "error": None if result_text else "[ERROR] System admin appears hung (no output).",
                            "session_id": out_session_id, "status": "DONE" if result_text else "ERROR"}
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
            if event_type == "assistant" and "message" in event:
                for block in event["message"].get("content", []):
                    if block.get("type") == "tool_use":
                        print(f"  [system] {block.get('name', '?')}({str(block.get('input', ''))[:100]})",
                              file=sys.stderr, flush=True)
                    elif block.get("type") == "text" and block.get("text"):
                        print(f"  [system] thinking: {block['text'][:120].replace(chr(10), ' ')}",
                              file=sys.stderr, flush=True)
            elif event_type == "result":
                result_text = event.get("result", "")
                result_cost = event.get("total_cost_usd", 0)
                result_turns = event.get("num_turns", "?")
                sid = event.get("session_id", "")
                if sid:
                    out_session_id = sid
                    print(f"  [system] Session: {sid[:12]}...", file=sys.stderr, flush=True)

        sel.close()
        proc.wait(timeout=10)
        _active_proc = None

        if not result_text:
            stderr = proc.stderr.read()
            return {"error": stderr.strip() or "[ERROR] No output from system admin.",
                    "session_id": out_session_id, "status": "ERROR"}

        status = "AWAITING_CONFIRMATION" if "CONFIRMATION REQUIRED" in result_text.upper() else "DONE"
        return {"text": result_text, "session_id": out_session_id, "turns": result_turns,
                "cost": result_cost, "status": status, "error": None}

    except FileNotFoundError:
        return {"error": f"[ERROR] Claude CLI not found at {CLAUDE_CLI}.", "status": "ERROR"}
    except Exception as e:
        _active_proc = None
        return {"error": f"[ERROR] Failed to run system admin: {e}", "status": "ERROR"}


@mcp.tool()
def system_admin(request: str, session_id: str = "", approve: bool = False) -> str:
    """
    Delegate a system-administration task on the user's Mac to a careful, gated
    Claude Code "system admin" (managing files, processes, services, installs,
    configuration, disk, network, logs — anything about the machine itself).

    Use this INSTEAD of trying to run system/shell operations another way. It runs
    READ-MOSTLY: it investigates freely but will NOT change anything without the
    user's explicit approval.

    APPROVAL FLOW — follow it exactly:
      1. Start a task: call system_admin(request="<what the user wants>"). Leave
         session_id empty and approve=false.
      2. If the result's STATUS is AWAITING_CONFIRMATION, the admin needs the
         user's OK before changing anything. Relay the "CONFIRMATION REQUIRED"
         details to the user and ask them to approve or decline. Do NOT approve on
         their behalf.
      3. When the user answers, call system_admin AGAIN with:
           - session_id = the SESSION value from the previous result (required),
           - request    = the user's decision, in their words,
           - approve    = true if they approved, false if they declined.
         This resumes the SAME session so the admin keeps full context.
      4. If STATUS is DONE, the task is finished — relay the summary to the user.

    Args:
        request: The system task to perform, or (when resuming) the user's
            decision about a pending CONFIRMATION REQUIRED action.
        session_id: Resume an existing admin session. REQUIRED when responding to
            an AWAITING_CONFIRMATION result — pass the SESSION value from it. Leave
            empty to start a fresh task.
        approve: Set true ONLY when the user has explicitly approved a pending
            CONFIRMATION REQUIRED action. It unlocks write/install/delete/sudo for
            this one resumed turn so the admin can carry out the approved steps.
            Never set true on a fresh request or without the user's go-ahead.
    """
    if not request.strip():
        return "[ERROR] Provide a request describing the system task or the user's decision."

    if approve and not session_id.strip():
        return ("[ERROR] approve=true requires the session_id of the pending task. "
                "Pass the SESSION value from the AWAITING_CONFIRMATION result.")

    res = _run_admin(request=request, approve=approve, session_id=session_id,
                     max_turns=DEFAULT_MAX_TURNS)

    status = res.get("status")
    sid = res.get("session_id", "")

    if status == "CANCELLED":
        return "[CANCELLED] System admin task was cancelled by user."
    if status == "ERROR" or res.get("error"):
        tail = f"\nSESSION: {sid}" if sid else ""
        return f"{res.get('error', '[ERROR] System admin failed.')}{tail}"

    text = res.get("text", "")
    if status == "AWAITING_CONFIRMATION":
        return (
            "STATUS: AWAITING_CONFIRMATION\n"
            f"SESSION: {sid}\n\n"
            f"{text}\n\n"
            "→ The system admin will NOT proceed until the user decides. Relay the "
            "above to the user and ask them to approve or decline. When they "
            f"respond, call system_admin again with session_id=\"{sid}\", "
            "approve=true if they approved (false if not), and request set to their "
            "decision."
        )

    cost = res.get("cost", 0) or 0
    turns = res.get("turns", "?")
    return (f"STATUS: DONE\nSESSION: {sid}\n\n{text}\n\n"
            f"[system admin: {turns} turns, ${cost:.4f}]")


if __name__ == "__main__":
    mcp.run(transport="stdio")
