"""
SQLite store for ingest watcher devices.

Each device that runs the folder-watcher client (PC, MacBook, ...) registers
itself here on startup and heartbeats periodically, so the dashboard's Devices
panel can show what's connected, which folders it watches, and how many files
it has sent. One table, ``devices``, lives in the shared database file
(``config.DB_PATH``) but owns its own connection, mirroring db.py /
project_store.py / calendar_store.py (module-level connection singleton + write
lock + dict-returning CRUD).

A device is identified by a stable ``device_id`` the client picks once and keeps
(its hostname, lowercased). Registration is idempotent: re-registering updates
the hostname/platform/watch_paths and refreshes ``last_seen`` without resetting
the ``files_sent`` counter or ``first_seen``.

This module only stores device state; it never talks to the devices. The
device-facing endpoints (register / heartbeat / upload) live in
dashboard/routes/ingest.py.
"""

import json
import time
import threading
import sqlite3

import config

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_devices_db():
    """Create the devices table if it doesn't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id   TEXT PRIMARY KEY,       -- stable client id (hostname)
            hostname    TEXT NOT NULL DEFAULT '',
            platform    TEXT NOT NULL DEFAULT '',  -- darwin | windows | linux
            watch_paths TEXT NOT NULL DEFAULT '[]', -- JSON array of folder paths
            files_sent  INTEGER NOT NULL DEFAULT 0,
            first_seen  REAL NOT NULL,
            last_seen   REAL NOT NULL
        );
    """)
    conn.commit()


def register_device(device_id: str, hostname: str, platform: str,
                    watch_paths: list[str]) -> None:
    """Idempotent upsert. Preserves files_sent and first_seen across restarts;
    refreshes hostname/platform/watch_paths and last_seen."""
    now = time.time()
    paths_json = json.dumps(watch_paths or [])
    with _lock:
        conn = _get_conn()
        conn.execute(
            """
            INSERT INTO devices (device_id, hostname, platform, watch_paths,
                                 files_sent, first_seen, last_seen)
            VALUES (?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                hostname    = excluded.hostname,
                platform    = excluded.platform,
                watch_paths = excluded.watch_paths,
                last_seen   = excluded.last_seen
            """,
            (device_id, hostname, platform, paths_json, now, now),
        )
        conn.commit()


def touch_device(device_id: str, files_sent_delta: int = 0) -> None:
    """Bump last_seen (heartbeat) and optionally increment the files_sent
    counter. No-op if the device was never registered."""
    now = time.time()
    with _lock:
        conn = _get_conn()
        conn.execute(
            "UPDATE devices SET last_seen = ?, files_sent = files_sent + ? "
            "WHERE device_id = ?",
            (now, files_sent_delta, device_id),
        )
        conn.commit()


def list_devices(online_window_seconds: float = 90.0) -> list[dict]:
    """Return all devices, newest-heartbeat first, with a computed ``online``
    flag (heartbeat seen within the window) and parsed watch_paths."""
    now = time.time()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM devices ORDER BY last_seen DESC"
    ).fetchall()
    devices = []
    for r in rows:
        try:
            paths = json.loads(r["watch_paths"])
        except (ValueError, TypeError):
            paths = []
        devices.append({
            "device_id": r["device_id"],
            "hostname": r["hostname"],
            "platform": r["platform"],
            "watch_paths": paths,
            "files_sent": r["files_sent"],
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
            "online": (now - r["last_seen"]) <= online_window_seconds,
        })
    return devices
