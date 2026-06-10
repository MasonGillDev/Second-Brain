"""
SQLite store for the project tracking toolkit.

Source of truth for projects and their tasks/notes. Shares the same database
file as db.py (config.DB_PATH) but owns its own connection — a second WAL
connection in the same process is fine. Mirrors db.py's idiom: a module-level
connection singleton, a write lock, and dict-returning CRUD.

Three tables:
  - projects:      one row per project (repo, dev machine, path, docs, etc.)
  - project_tasks: tasks belonging to a project (status + priority tracked)
  - project_notes: freeform notes belonging to a project
"""

import os
import time
import threading
import sqlite3

import config

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("PRAGMA busy_timeout=5000")
        _conn.execute("PRAGMA foreign_keys=ON")  # honor ON DELETE CASCADE
        init_projects_db(_conn)
    return _conn


def init_projects_db(conn: sqlite3.Connection | None = None):
    """Create the project tables and indexes if they don't exist."""
    conn = conn or _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL UNIQUE,
            github_repo      TEXT    NOT NULL DEFAULT '',
            dev_machine      TEXT    NOT NULL DEFAULT '',
            path             TEXT    NOT NULL DEFAULT '',
            similar_projects TEXT    NOT NULL DEFAULT '',
            docs_path        TEXT    NOT NULL DEFAULT '',
            created_at       REAL    NOT NULL,
            updated_at       REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS project_tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name         TEXT    NOT NULL,
            description  TEXT    NOT NULL DEFAULT '',
            status       TEXT    NOT NULL DEFAULT 'todo',
            priority     TEXT    NOT NULL DEFAULT 'med',
            github_issue TEXT    NOT NULL DEFAULT '',
            created_at   REAL    NOT NULL,
            updated_at   REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS project_notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name        TEXT    NOT NULL DEFAULT '',
            description TEXT    NOT NULL DEFAULT '',
            created_at  REAL    NOT NULL,
            updated_at  REAL    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_project_tasks_project ON project_tasks(project_id);
        CREATE INDEX IF NOT EXISTS idx_project_notes_project ON project_notes(project_id);
    """)
    conn.commit()


# Columns clients are allowed to set on update (id/timestamps are managed here).
_PROJECT_FIELDS = ("name", "github_repo", "dev_machine", "path", "similar_projects", "docs_path")
_TASK_FIELDS = ("name", "description", "status", "priority", "github_issue")
_NOTE_FIELDS = ("name", "description")

VALID_STATUSES = ("todo", "in_progress", "done")
VALID_PRIORITIES = ("low", "med", "high")


def _resolve_project_id(conn: sqlite3.Connection, project) -> int | None:
    """Resolve a project reference (int id or name string) to its id."""
    if isinstance(project, int) or (isinstance(project, str) and project.isdigit()):
        row = conn.execute("SELECT id FROM projects WHERE id = ?", (int(project),)).fetchone()
    else:
        row = conn.execute("SELECT id FROM projects WHERE name = ?", (str(project),)).fetchone()
    return row["id"] if row else None


# ---- Projects ----

def create_project(name: str, github_repo: str = "", dev_machine: str = "",
                   path: str = "", similar_projects: str = "", docs_path: str = "") -> dict:
    """Insert a project. Raises ValueError if the name already exists."""
    name = name.strip()
    if not name:
        raise ValueError("Project name is required.")
    now = time.time()
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO projects (name, github_repo, dev_machine, path, similar_projects, "
                "docs_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, github_repo.strip(), dev_machine.strip(), path.strip(),
                 similar_projects.strip(), docs_path.strip(), now, now),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"A project named '{name}' already exists.")
    return get_project(cur.lastrowid)


def list_projects() -> list[dict]:
    """All projects with task/note counts, most recently updated first."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT p.*,
            (SELECT COUNT(*) FROM project_tasks t WHERE t.project_id = p.id) AS task_count,
            (SELECT COUNT(*) FROM project_tasks t WHERE t.project_id = p.id AND t.status != 'done') AS open_task_count,
            (SELECT COUNT(*) FROM project_notes n WHERE n.project_id = p.id) AS note_count
        FROM projects p
        ORDER BY p.updated_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def get_project(project) -> dict | None:
    """Fetch one project (by id or name) with task/note counts."""
    conn = _get_conn()
    pid = _resolve_project_id(conn, project)
    if pid is None:
        return None
    row = conn.execute("""
        SELECT p.*,
            (SELECT COUNT(*) FROM project_tasks t WHERE t.project_id = p.id) AS task_count,
            (SELECT COUNT(*) FROM project_tasks t WHERE t.project_id = p.id AND t.status != 'done') AS open_task_count,
            (SELECT COUNT(*) FROM project_notes n WHERE n.project_id = p.id) AS note_count
        FROM projects p WHERE p.id = ?
    """, (pid,)).fetchone()
    return dict(row) if row else None


def update_project(project, **fields) -> dict | None:
    """Update a project's columns. Unknown/empty-string keys are ignored."""
    conn = _get_conn()
    pid = _resolve_project_id(conn, project)
    if pid is None:
        return None
    sets = {k: v for k, v in fields.items() if k in _PROJECT_FIELDS and v is not None}
    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        with _lock:
            conn.execute(
                f"UPDATE projects SET {cols}, updated_at = ? WHERE id = ?",
                [*sets.values(), time.time(), pid],
            )
            conn.commit()
    return get_project(pid)


def delete_project(project) -> bool:
    """Delete a project and (via cascade) its tasks and notes."""
    conn = _get_conn()
    pid = _resolve_project_id(conn, project)
    if pid is None:
        return False
    with _lock:
        conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
        conn.commit()
    return True


# ---- Tasks ----

def create_task(project, name: str, description: str = "", priority: str = "med",
                status: str = "todo") -> dict | None:
    """Add a task to a project. Returns None if the project isn't found."""
    name = name.strip()
    if not name:
        raise ValueError("Task name is required.")
    conn = _get_conn()
    pid = _resolve_project_id(conn, project)
    if pid is None:
        return None
    now = time.time()
    with _lock:
        cur = conn.execute(
            "INSERT INTO project_tasks (project_id, name, description, status, priority, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pid, name, description, status, priority, now, now),
        )
        conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, pid))
        conn.commit()
    return get_task(cur.lastrowid)


def list_tasks(project, status: str | None = None) -> list[dict]:
    """Tasks for a project, optionally filtered by status. Newest first."""
    conn = _get_conn()
    pid = _resolve_project_id(conn, project)
    if pid is None:
        return []
    if status:
        rows = conn.execute(
            "SELECT * FROM project_tasks WHERE project_id = ? AND status = ? ORDER BY created_at DESC",
            (pid, status),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM project_tasks WHERE project_id = ? ORDER BY created_at DESC", (pid,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_task(task_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM project_tasks WHERE id = ?", (int(task_id),)).fetchone()
    return dict(row) if row else None


def update_task(task_id: int, **fields) -> dict | None:
    """Update a task's columns. Unknown/empty-string keys are ignored."""
    conn = _get_conn()
    sets = {k: v for k, v in fields.items() if k in _TASK_FIELDS and v is not None and v != ""}
    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        with _lock:
            cur = conn.execute(
                f"UPDATE project_tasks SET {cols}, updated_at = ? WHERE id = ?",
                [*sets.values(), time.time(), int(task_id)],
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
    return get_task(task_id)


def delete_task(task_id: int) -> bool:
    conn = _get_conn()
    with _lock:
        cur = conn.execute("DELETE FROM project_tasks WHERE id = ?", (int(task_id),))
        conn.commit()
    return cur.rowcount > 0


# ---- Notes ----

def create_note(project, name: str = "", description: str = "") -> dict | None:
    """Add a note to a project. Returns None if the project isn't found."""
    conn = _get_conn()
    pid = _resolve_project_id(conn, project)
    if pid is None:
        return None
    now = time.time()
    with _lock:
        cur = conn.execute(
            "INSERT INTO project_notes (project_id, name, description, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (pid, name.strip(), description, now, now),
        )
        conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, pid))
        conn.commit()
    return get_note(cur.lastrowid)


def list_notes(project) -> list[dict]:
    conn = _get_conn()
    pid = _resolve_project_id(conn, project)
    if pid is None:
        return []
    rows = conn.execute(
        "SELECT * FROM project_notes WHERE project_id = ? ORDER BY created_at DESC", (pid,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_note(note_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM project_notes WHERE id = ?", (int(note_id),)).fetchone()
    return dict(row) if row else None


def update_note(note_id: int, **fields) -> dict | None:
    conn = _get_conn()
    sets = {k: v for k, v in fields.items() if k in _NOTE_FIELDS and v is not None}
    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        with _lock:
            cur = conn.execute(
                f"UPDATE project_notes SET {cols}, updated_at = ? WHERE id = ?",
                [*sets.values(), time.time(), int(note_id)],
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
    return get_note(note_id)


def delete_note(note_id: int) -> bool:
    conn = _get_conn()
    with _lock:
        cur = conn.execute("DELETE FROM project_notes WHERE id = ?", (int(note_id),))
        conn.commit()
    return cur.rowcount > 0
