"""Live activity log stream."""

import json
from quart import Blueprint, jsonify, request, current_app
from dashboard.auth import require_auth

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/api/logs")
@require_auth
async def get_logs():
    """Return recent log entries. Use ?since=<index> for incremental fetches."""
    buf = current_app.log_buffer
    since = request.args.get("since", 0, type=int)
    snapshot = list(buf)
    entries = snapshot[since:] if since < len(snapshot) else []
    return jsonify({
        "entries": entries,
        "next": len(snapshot),
        "total": len(snapshot),
    })
