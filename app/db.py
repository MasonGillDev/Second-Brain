"""
SQLite database for cost tracking and persistent logs.

Two tables:
  - api_calls: Every Anthropic API call with tokens, cost, and source
  - logs: All stdout log messages, persisted across restarts
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
    return _conn


def init_db():
    """Create tables and indexes if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS api_calls (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        REAL    NOT NULL,
            source           TEXT    NOT NULL,
            model            TEXT    NOT NULL,
            input_tokens     INTEGER NOT NULL DEFAULT 0,
            output_tokens    INTEGER NOT NULL DEFAULT 0,
            cost_usd         REAL    NOT NULL DEFAULT 0.0,
            tool_calls_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL    NOT NULL,
            level     TEXT    NOT NULL DEFAULT 'info',
            source    TEXT    NOT NULL DEFAULT '',
            message   TEXT    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_api_calls_timestamp ON api_calls(timestamp);
        CREATE INDEX IF NOT EXISTS idx_api_calls_source ON api_calls(source);
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source);
    """)
    # Migration: add `details` column for full, expandable log content
    # (full tool args + result, full agent replies). NULL for plain log lines.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(logs)").fetchall()}
    if "details" not in cols:
        conn.execute("ALTER TABLE logs ADD COLUMN details TEXT")
    conn.commit()

    # Project tracking toolkit tables live in the same DB file but own their
    # connection (see project_store.py). Ensure they exist at startup too.
    import project_store
    project_store.init_projects_db()


# ---- Write operations ----

def log_api_call(source: str, model: str, input_tokens: int, output_tokens: int,
                 cost_usd: float, tool_calls_count: int = 0):
    """Record an API call with token usage and cost."""
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO api_calls (timestamp, source, model, input_tokens, output_tokens, cost_usd, tool_calls_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), source, model, input_tokens, output_tokens, cost_usd, tool_calls_count),
        )
        conn.commit()


def log_message(level: str, source: str, message: str, details: str | None = None):
    """Persist a log message. `details` holds full, expandable content (optional)."""
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO logs (timestamp, level, source, message, details) VALUES (?, ?, ?, ?, ?)",
            (time.time(), level, source, message, details),
        )
        conn.commit()


def prune_logs(max_age_days: float) -> int:
    """Delete log entries older than max_age_days. Returns rows removed."""
    if max_age_days <= 0:
        return 0
    cutoff = time.time() - max_age_days * 86400
    with _lock:
        conn = _get_conn()
        cur = conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
        conn.commit()
        return cur.rowcount


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost in USD for a given model and token counts."""
    rates = config.MODEL_COSTS.get(model, {"input": config.INPUT_COST_PER_1K, "output": config.OUTPUT_COST_PER_1K})
    return (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"]


# ---- Read operations ----

def get_api_calls(since: float | None = None, until: float | None = None,
                  source: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
    """Fetch API call records with optional filters."""
    conn = _get_conn()
    clauses, params = [], []
    if since is not None:
        clauses.append("timestamp >= ?")
        params.append(since)
    if until is not None:
        clauses.append("timestamp <= ?")
        params.append(until)
    if source is not None:
        clauses.append("source = ?")
        params.append(source)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM api_calls {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    return [dict(r) for r in rows]


def get_api_calls_count(since: float | None = None, until: float | None = None,
                        source: str | None = None) -> int:
    """Count API calls matching filters."""
    conn = _get_conn()
    clauses, params = [], []
    if since is not None:
        clauses.append("timestamp >= ?")
        params.append(since)
    if until is not None:
        clauses.append("timestamp <= ?")
        params.append(until)
    if source is not None:
        clauses.append("source = ?")
        params.append(source)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    row = conn.execute(f"SELECT COUNT(*) FROM api_calls {where}", params).fetchone()
    return row[0]


def get_cost_summary(since: float | None = None, until: float | None = None,
                     group_by: str = "day") -> dict:
    """Aggregated cost data. group_by: 'day' or 'source'."""
    conn = _get_conn()
    clauses, params = [], []
    if since is not None:
        clauses.append("timestamp >= ?")
        params.append(since)
    if until is not None:
        clauses.append("timestamp <= ?")
        params.append(until)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    # Totals
    totals_row = conn.execute(
        f"SELECT COALESCE(SUM(cost_usd),0) as cost, COALESCE(SUM(input_tokens),0) as inp, "
        f"COALESCE(SUM(output_tokens),0) as out, COUNT(*) as calls FROM api_calls {where}",
        params,
    ).fetchone()
    totals = {"cost_usd": totals_row[0], "input_tokens": totals_row[1],
              "output_tokens": totals_row[2], "call_count": totals_row[3]}

    # Breakdown
    if group_by == "source":
        group_col = "source"
        label_expr = "source"
    else:
        group_col = "date(timestamp, 'unixepoch', 'localtime')"
        label_expr = group_col

    rows = conn.execute(
        f"SELECT {label_expr} as label, SUM(cost_usd) as cost, SUM(input_tokens) as inp, "
        f"SUM(output_tokens) as out, COUNT(*) as calls FROM api_calls {where} "
        f"GROUP BY {group_col} ORDER BY label",
        params,
    ).fetchall()
    breakdown = [{"label": r[0], "cost_usd": r[1], "input_tokens": r[2],
                  "output_tokens": r[3], "call_count": r[4]} for r in rows]

    return {"totals": totals, "breakdown": breakdown}


def get_cost_by_source(since: float | None = None, until: float | None = None) -> list[dict]:
    """Spending grouped by source."""
    conn = _get_conn()
    clauses, params = [], []
    if since is not None:
        clauses.append("timestamp >= ?")
        params.append(since)
    if until is not None:
        clauses.append("timestamp <= ?")
        params.append(until)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT source, SUM(cost_usd) as cost, COUNT(*) as calls, "
        f"SUM(input_tokens) as inp, SUM(output_tokens) as out "
        f"FROM api_calls {where} GROUP BY source ORDER BY cost DESC",
        params,
    ).fetchall()
    return [{"source": r[0], "cost_usd": r[1], "call_count": r[2],
             "input_tokens": r[3], "output_tokens": r[4]} for r in rows]


def get_logs(since_id: int = 0, limit: int = 500) -> list[dict]:
    """Fetch logs newer than since_id for incremental polling."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM logs WHERE id > ? ORDER BY id ASC LIMIT ?",
        (since_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_logs_range(since_ts: float | None = None, until_ts: float | None = None,
                   source: str | None = None, level: str | None = None,
                   limit: int = 500, offset: int = 0) -> list[dict]:
    """Fetch logs with filters for historical browsing."""
    conn = _get_conn()
    clauses, params = [], []
    if since_ts is not None:
        clauses.append("timestamp >= ?")
        params.append(since_ts)
    if until_ts is not None:
        clauses.append("timestamp <= ?")
        params.append(until_ts)
    if source is not None:
        clauses.append("source = ?")
        params.append(source)
    if level is not None:
        clauses.append("level = ?")
        params.append(level)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM logs {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    return [dict(r) for r in rows]
