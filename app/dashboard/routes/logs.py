"""Activity log endpoints — reads from SQLite."""

import asyncio
from datetime import datetime, timedelta
from quart import Blueprint, jsonify, request
from dashboard.auth import require_auth
import db

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/api/logs")
@require_auth
async def get_logs():
    """Fetch logs from SQLite. Supports incremental polling via ?since_id= and filtering."""
    since_id = request.args.get("since_id", 0, type=int)
    source = request.args.get("source") or None
    level = request.args.get("level") or None
    limit = request.args.get("limit", 200, type=int)

    since_ts = None
    until_ts = None
    since_date = request.args.get("since")
    until_date = request.args.get("until")
    if since_date:
        try:
            since_ts = datetime.strptime(since_date, "%Y-%m-%d").timestamp()
        except ValueError:
            pass
    if until_date:
        try:
            until_ts = (datetime.strptime(until_date, "%Y-%m-%d") + timedelta(days=1)).timestamp()
        except ValueError:
            pass

    if since_id > 0:
        entries = await asyncio.to_thread(db.get_logs, since_id=since_id, limit=limit)
        if source:
            entries = [e for e in entries if e["source"] == source]
        if level:
            entries = [e for e in entries if e["level"] == level]
    else:
        entries = await asyncio.to_thread(db.get_logs_range, since_ts=since_ts, until_ts=until_ts,
                                          source=source, level=level,
                                          limit=limit, offset=0)

    max_id = entries[-1]["id"] if entries else since_id
    return jsonify({"entries": entries, "next_id": max_id, "count": len(entries)})
