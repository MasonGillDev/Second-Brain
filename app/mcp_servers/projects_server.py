"""
Projects MCP Server.

The agent's interface to the project tracking toolkit. Projects, tasks, and
notes live in SQLite (project_store) as the source of truth; get_project_context
aggregates everything we know about a project — DB record, docs, GitHub
(issues/PRs/commits via ToolGate) and recent Claude Code sessions (via Claude
Hub) — into one bundle for the agent to reason over.

All the heavy lifting lives in project_store.py and project_context.py; this
server is a thin, well-described wrapper that returns readable text.
"""

import sys
import os
import socket

# Add project root (app/) to path so we can import the shared modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

import project_store as store
import project_context as pctx
import project_index as pidx

mcp = FastMCP("projects")


def _fmt_project_line(p: dict) -> str:
    bits = []
    if p.get("github_repo"):
        bits.append(f"repo {p['github_repo']}")
    if p.get("dev_machine"):
        bits.append(f"on {p['dev_machine']}")
    bits.append(f"{p.get('open_task_count', 0)}/{p.get('task_count', 0)} open tasks")
    if p.get("note_count"):
        bits.append(f"{p['note_count']} notes")
    meta = "  ·  ".join(bits)
    return f"- [{p['id']}] {p['name']}\n    {meta}"


def _fmt_task_line(t: dict) -> str:
    issue = f"  ({t['github_issue']})" if t.get("github_issue") else ""
    desc = f"\n      {t['description']}" if t.get("description") else ""
    return f"  - [{t['id']}] {t['name']} — {t['status']}/{t['priority']}{issue}{desc}"


def _not_found(project) -> str:
    """Not-found message that also lists the real project names, so the agent
    can correct a near-miss (e.g. 'Art of war' -> 'Art-Of-War') without guessing."""
    names = [p["name"] for p in store.list_projects()]
    if not names:
        return (f"No project found matching '{project}'. "
                "There are no projects yet — use create_project to add one.")
    return (f"No project found matching '{project}'. "
            f"Available projects: {', '.join(names)}")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@mcp.tool()
def create_project(name: str, github_repo: str = "", dev_machine: str = "",
                   path: str = "", similar_projects: str = "", docs_path: str = "") -> str:
    """
    Create a project — the durable record of something you work on.

    Args:
        name: Unique project name (e.g. "Second-Brain").
        github_repo: GitHub repo as "owner/repo", or just the repo name (the
            owner is resolved automatically). Leave blank if none.
        dev_machine: The computer you develop this on. Defaults to THIS machine's
            hostname if left blank.
        path: Absolute path to the project on disk (e.g. "/Users/you/repo").
        similar_projects: Comma-separated names of related projects, if any.
        docs_path: Absolute path to a folder of docs for this project.
    """
    if not dev_machine.strip():
        dev_machine = socket.gethostname()
    try:
        p = store.create_project(name, github_repo, dev_machine, path, similar_projects, docs_path)
    except ValueError as e:
        return str(e)
    return f"Created project [{p['id']}] '{p['name']}'."


@mcp.tool()
def list_projects() -> str:
    """List all tracked projects with their repo, machine, and open-task counts."""
    projects = store.list_projects()
    if not projects:
        return "No projects yet. Use create_project to add one."
    return f"Projects ({len(projects)}):\n" + "\n".join(_fmt_project_line(p) for p in projects)


@mcp.tool()
def get_project(project: str) -> str:
    """
    Get one project's full record (by name or id), with its tasks and notes counts.

    Args:
        project: Project name or id.
    """
    p = store.get_project(project)
    if p is None:
        return _not_found(project)
    lines = [
        f"[{p['id']}] {p['name']}",
        f"  github_repo: {p.get('github_repo') or '—'}",
        f"  dev_machine: {p.get('dev_machine') or '—'}",
        f"  path: {p.get('path') or '—'}",
        f"  docs_path: {p.get('docs_path') or '—'}",
        f"  similar_projects: {p.get('similar_projects') or '—'}",
        f"  tasks: {p.get('open_task_count', 0)} open / {p.get('task_count', 0)} total"
        f"  ·  notes: {p.get('note_count', 0)}",
    ]
    return "\n".join(lines)


@mcp.tool()
def update_project(project: str, name: str = "", github_repo: str = "", dev_machine: str = "",
                   path: str = "", similar_projects: str = "", docs_path: str = "") -> str:
    """
    Update fields on a project. Only non-empty arguments are changed.

    Args:
        project: Project name or id to update.
        name, github_repo, dev_machine, path, similar_projects, docs_path:
            New values (leave blank to keep the current value).
    """
    fields = {k: v for k, v in {
        "name": name, "github_repo": github_repo, "dev_machine": dev_machine,
        "path": path, "similar_projects": similar_projects, "docs_path": docs_path,
    }.items() if v.strip()}
    if not fields:
        return "Nothing to update — provide at least one field."
    p = store.update_project(project, **fields)
    if p is None:
        return _not_found(project)
    return f"Updated project '{p['name']}': {', '.join(fields)}."


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@mcp.tool()
def create_task(project: str, name: str, description: str = "", priority: str = "med") -> str:
    """
    Add a task to a project.

    Args:
        project: Project name or id.
        name: Short task title.
        description: Optional longer detail.
        priority: One of low, med, high (default med).
    """
    if priority not in store.VALID_PRIORITIES:
        return f"priority must be one of {', '.join(store.VALID_PRIORITIES)}."
    t = store.create_task(project, name, description, priority)
    if t is None:
        return _not_found(project)
    return f"Created task [{t['id']}] '{t['name']}' ({t['priority']}) in '{project}'."


@mcp.tool()
def get_tasks(project: str, status: str = "") -> str:
    """
    List a project's tasks, optionally filtered by status.

    Args:
        project: Project name or id.
        status: Optional filter — todo, in_progress, or done.
    """
    if store.get_project(project) is None:
        return _not_found(project)
    if status and status not in store.VALID_STATUSES:
        return f"status must be one of {', '.join(store.VALID_STATUSES)}."
    tasks = store.list_tasks(project, status or None)
    if not tasks:
        return f"No {status + ' ' if status else ''}tasks for '{project}'."
    return f"Tasks for '{project}':\n" + "\n".join(_fmt_task_line(t) for t in tasks)


@mcp.tool()
def set_task(task_id: int, status: str = "", priority: str = "", name: str = "",
             description: str = "") -> str:
    """
    Update a task. Only non-empty arguments are changed.

    Args:
        task_id: The task's id (from get_tasks).
        status: New status — todo, in_progress, or done.
        priority: New priority — low, med, high.
        name: New title.
        description: New detail.
    """
    if status and status not in store.VALID_STATUSES:
        return f"status must be one of {', '.join(store.VALID_STATUSES)}."
    if priority and priority not in store.VALID_PRIORITIES:
        return f"priority must be one of {', '.join(store.VALID_PRIORITIES)}."
    t = store.update_task(task_id, status=status, priority=priority, name=name, description=description)
    if t is None:
        return f"No task found with id {task_id}."
    return f"Updated task [{t['id']}] '{t['name']}' — {t['status']}/{t['priority']}."


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@mcp.tool()
def create_note(project: str, name: str = "", description: str = "") -> str:
    """
    Add a note to a project (a fact, decision, or reminder).

    Args:
        project: Project name or id.
        name: Short note title.
        description: The note body.
    """
    n = store.create_note(project, name, description)
    if n is None:
        return _not_found(project)
    return f"Added note [{n['id']}] to '{project}'."


@mcp.tool()
def get_notes(project: str) -> str:
    """
    List a project's notes.

    Args:
        project: Project name or id.
    """
    if store.get_project(project) is None:
        return _not_found(project)
    notes = store.list_notes(project)
    if not notes:
        return f"No notes for '{project}'."
    lines = [f"  - [{n['id']}] {n.get('name') or '(untitled)'}: {n.get('description', '')}" for n in notes]
    return f"Notes for '{project}':\n" + "\n".join(lines)


@mcp.tool()
def set_note(note_id: int, name: str = "", description: str = "") -> str:
    """
    Update a note. Only non-empty arguments are changed.

    Args:
        note_id: The note's id (from get_notes).
        name: New title.
        description: New body.
    """
    fields = {k: v for k, v in {"name": name, "description": description}.items() if v}
    if not fields:
        return "Nothing to update — provide a name or description."
    n = store.update_note(note_id, **fields)
    if n is None:
        return f"No note found with id {note_id}."
    return f"Updated note [{n['id']}]."


# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------

@mcp.tool()
def get_docs(project: str) -> str:
    """
    List the document filenames under a project's docs_path.

    Args:
        project: Project name or id.
    """
    p = store.get_project(project)
    if p is None:
        return _not_found(project)
    if not p.get("docs_path"):
        return f"'{p['name']}' has no docs_path set."
    docs = pctx.list_docs(p["docs_path"])
    if not docs:
        return f"No docs found under {p['docs_path']}."
    return f"Docs for '{p['name']}' ({len(docs)}):\n" + "\n".join(f"  - {d}" for d in docs)


@mcp.tool()
def get_doc(project: str, filename: str) -> str:
    """
    Return the full text of one document for a project.

    Args:
        project: Project name or id.
        filename: A filename from get_docs (relative to the project's docs_path).
    """
    p = store.get_project(project)
    if p is None:
        return _not_found(project)
    try:
        return pctx.read_doc(p.get("docs_path", ""), filename)
    except (FileNotFoundError, ValueError) as e:
        return str(e)


# ---------------------------------------------------------------------------
# Context (headline) + actions
# ---------------------------------------------------------------------------

@mcp.tool()
def get_project_context(project: str) -> str:
    """
    Gather EVERYTHING known about a project into one bundle: its record, tasks
    (by status), notes, doc list, GitHub issues/pull-requests/recent-commits,
    and recent Claude Code sessions. Use this to get fully up to speed on a
    project before working on it — it saves you from making many small calls.

    Args:
        project: Project name or id.
    """
    ctx = pctx.gather_context(project)
    if "error" in ctx:  # only set when the project itself isn't found
        return _not_found(project)
    text = pctx.format_context(ctx)
    text += "\n\nTip: search_project does semantic search across this project's docs/tasks/notes/commits — use it instead of reading whole docs."
    return text


@mcp.tool()
def search_project(project: str, query: str, source_type: str = "", top_k: int = 8) -> str:
    """
    Semantic search across a project's indexed content — docs (chunked), tasks,
    notes, and commits. Returns the most relevant SNIPPETS with a reference, so
    you can pull the full item afterward (get_doc by filename, get_tasks/get_notes
    by id, or look up the commit by sha). Use this instead of reading whole docs.

    Docs/tasks/notes are auto-synced on each search; run reindex_project to also
    pick up new commits.

    Args:
        project: Project name or id.
        query: What to look for, as a natural-language phrase.
        source_type: Optional filter — doc, task, note, or commit (blank = all).
        top_k: Max snippets to return (default 8).
    """
    st = source_type.strip() or None
    if st and st not in ("doc", "task", "note", "commit"):
        return "source_type must be one of: doc, task, note, commit (or blank for all)."
    try:
        results = pidx.search_project(project, query, source_type=st, top_k=top_k)
    except ValueError:
        return _not_found(project)
    except Exception as e:  # noqa: BLE001 — surface Chroma/embedding errors cleanly
        return f"Search unavailable: {e}"
    if not results:
        return (f"No matches in '{project}' for that query. "
                "If you just added content, run reindex_project first.")
    lines = [f"Matches in '{project}':"]
    for r in results:
        lines.append(f"  [{r['relevance']:.2f}] {r['source_type']} «{r['ref']}» — {r['title']}")
        lines.append(f"      {r['snippet']}")
    lines.append("\nFetch full content with get_doc (ref = filename), get_tasks/get_notes (by id), "
                 "or look up a commit by its sha.")
    return "\n".join(lines)


@mcp.tool()
def reindex_project(project: str) -> str:
    """
    (Re)build a project's search index from its docs, tasks, notes, and commits.
    Idempotent — unchanged docs and already-seen commits are skipped. Run this
    after adding commits or to force a full refresh (search_project already keeps
    docs/tasks/notes current on its own).

    Args:
        project: Project name or id.
    """
    try:
        c = pidx.reindex_project(project)
    except ValueError:
        return _not_found(project)
    except Exception as e:  # noqa: BLE001
        return f"Reindex failed: {e}"
    return (f"Indexed '{project}': {c['docs']} doc chunks, {c['tasks']} tasks, "
            f"{c['notes']} notes, {c['commits']} commits (new/changed).")


@mcp.tool()
def push_task_to_github(task_id: int) -> str:
    """
    Create a GitHub issue from a tracked task (using the project's repo) and
    record the issue reference back on the task.

    Args:
        task_id: The task's id (from get_tasks).
    """
    t = store.get_task(task_id)
    if t is None:
        return f"No task found with id {task_id}."
    p = store.get_project(t["project_id"])
    if p is None:
        return "That task's project no longer exists."
    if t.get("github_issue"):
        return f"Task already linked to {t['github_issue']}."
    try:
        issue = pctx.create_github_issue(p.get("github_repo", ""), t["name"], t.get("description", ""))
    except pctx.ToolGateError as e:
        return f"Couldn't create the issue: {e}"
    ref = issue.get("html_url") or (f"#{issue['number']}" if issue.get("number") else "(created)")
    store.update_task(task_id, github_issue=ref)
    return f"Created GitHub issue for task '{t['name']}': {ref}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
