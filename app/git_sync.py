"""
Git sync service for tracked projects.

Keeps the local clones of tracked projects current with GitHub so the rest of the
toolkit (docs, search index, context) operates on fresh code. Polling model: a
launchd job runs run_once() on an interval; it fetches every auto-sync project and
fast-forwards the ones that are cleanly behind. Dirty or diverged repos are skipped
and flagged — local work is never touched. A project that actually updates gets its
search index refreshed (reindex_project).

Same module is imported by the dashboard route and the MCP tool (sync_one) so a
"pull now" goes through the exact same logic.

git runs with GIT_TERMINAL_PROMPT=0 so a missing credential fails fast instead of
hanging. Auth uses whatever the machine already has (osxkeychain helper here).
"""

import os
import sys
import subprocess

# Run standalone (launchd) as well as imported — put app/ on the path either way.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import db
import project_store as store

# Statuses that mean "we left the repo alone on purpose" (warning, not error).
_SKIP_STATUSES = {"dirty", "diverged", "detached", "no_upstream", "not_cloned"}


def _git(path: str, *args: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run `git -C path <args>`; return (returncode, stdout, stderr)."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        r = subprocess.run(
            ["git", "-C", path, *args],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "git command timed out"
    except OSError as e:
        return 1, "", str(e)


def sync_project(record: dict, vector_store=None) -> dict:
    """Fetch + fast-forward one project's clone. Returns a result dict and records
    the outcome on the project row + the Activity Log."""
    pid = record.get("id")
    name = record.get("name", "?")
    path = record.get("path", "")

    def finish(status: str, message: str = "", head: str = "") -> dict:
        store.set_sync_state(pid, status, message, head)
        level = "error" if status == "error" else ("warning" if status in _SKIP_STATUSES else "info")
        try:
            db.log_message(level, "gitsync", f"{name}: {status}" + (f" — {message}" if message else ""))
        except Exception:
            pass
        return {"project_id": pid, "name": name, "status": status, "message": message, "head": head}

    if not path:
        return finish("not_cloned", "no path set")
    if not os.path.isdir(path) or not os.path.isdir(os.path.join(path, ".git")):
        return finish("not_cloned", f"no git clone at {path}")

    timeout = getattr(config, "GIT_SYNC_FETCH_TIMEOUT", 120)

    rc, out, err = _git(path, "fetch", "--prune", "origin", timeout=timeout)
    if rc != 0:
        return finish("error", f"fetch failed: {(err or out)[:200]}")

    rc, branch, _ = _git(path, "rev-parse", "--abbrev-ref", "HEAD")
    if rc != 0:
        return finish("error", "couldn't read current branch")
    if branch == "HEAD":
        return finish("detached", "detached HEAD")

    rc, upstream, _ = _git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if rc != 0 or not upstream:
        return finish("no_upstream", f"branch '{branch}' has no upstream")

    rc, porcelain, _ = _git(path, "status", "--porcelain")
    if rc == 0 and porcelain:
        return finish("dirty", "uncommitted local changes")

    _, head_before, _ = _git(path, "rev-parse", "--short", "HEAD")

    rc, counts, _ = _git(path, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    ahead = behind = 0
    if rc == 0:
        try:
            ahead, behind = (int(x) for x in counts.split())
        except ValueError:
            pass

    if behind == 0:
        return finish("up_to_date", f"{branch} up to date", head_before)
    if ahead > 0:
        return finish("diverged", f"{ahead} ahead / {behind} behind {upstream}", head_before)

    # Cleanly behind → fast-forward only (never creates a merge commit).
    rc, out, err = _git(path, "merge", "--ff-only", upstream, timeout=timeout)
    if rc != 0:
        return finish("error", f"ff-only merge failed: {(err or out)[:200]}")
    _, head_after, _ = _git(path, "rev-parse", "--short", "HEAD")

    if getattr(config, "GIT_SYNC_REINDEX_ON_CHANGE", True):
        try:
            import project_index
            project_index.reindex_project(pid, vector_store=vector_store)
        except Exception as e:  # noqa: BLE001 — never let reindex failure fail the sync
            try:
                db.log_message("warning", "gitsync", f"{name}: reindex after pull failed: {e}")
            except Exception:
                pass

    return finish("updated", f"{behind} commit(s) → {head_after}", head_after)


def sync_one(project, vector_store=None) -> dict:
    """Sync a single project by id/name (used by the MCP tool + dashboard route)."""
    rec = store.get_project(project)
    if rec is None:
        return {"project_id": None, "name": str(project), "status": "not_found",
                "message": "no such project", "head": ""}
    return sync_project(rec, vector_store=vector_store)


def sync_all(vector_store=None) -> list[dict]:
    """Sync every project with auto_sync on, sequentially."""
    results = []
    for p in store.list_projects():
        if not p.get("auto_sync", 1):
            continue
        results.append(sync_project(p, vector_store=vector_store))
    return results


def run_once():
    """One sweep over all auto-sync projects, then exit (launchd StartInterval)."""
    db.init_db()
    config.reload_overrides()
    if not getattr(config, "GIT_SYNC_ENABLED", True):
        print("[gitsync] disabled via config; skipping run.")
        return
    results = sync_all()
    tally: dict[str, int] = {}
    for r in results:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(tally.items())) or "no projects"
    print(f"[gitsync] swept {len(results)} project(s): {summary}")


if __name__ == "__main__":
    run_once()
