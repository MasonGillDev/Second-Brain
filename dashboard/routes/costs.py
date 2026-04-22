"""API cost tracking endpoints."""

from datetime import datetime, timedelta
from quart import Blueprint, jsonify, request
from dashboard.auth import require_auth
import db

costs_bp = Blueprint("costs", __name__)


def _parse_date(s: str | None) -> float | None:
    """Parse YYYY-MM-DD string to epoch timestamp, or None."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").timestamp()
    except ValueError:
        return None


def _parse_date_end(s: str | None) -> float | None:
    """Parse YYYY-MM-DD to end-of-day epoch timestamp, or None."""
    if not s:
        return None
    try:
        dt = datetime.strptime(s, "%Y-%m-%d") + timedelta(days=1)
        return dt.timestamp()
    except ValueError:
        return None


@costs_bp.route("/api/costs/summary")
@require_auth
async def cost_summary():
    """Aggregated cost data, optionally grouped by day or source."""
    since = _parse_date(request.args.get("since"))
    until = _parse_date_end(request.args.get("until"))
    group_by = request.args.get("group_by", "day")
    data = db.get_cost_summary(since=since, until=until, group_by=group_by)
    return jsonify(data)


@costs_bp.route("/api/costs/calls")
@require_auth
async def cost_calls():
    """Paginated list of individual API calls."""
    since = _parse_date(request.args.get("since"))
    until = _parse_date_end(request.args.get("until"))
    source = request.args.get("source") or None
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    calls = db.get_api_calls(since=since, until=until, source=source, limit=limit, offset=offset)
    total = db.get_api_calls_count(since=since, until=until, source=source)
    return jsonify({"calls": calls, "total_count": total})


@costs_bp.route("/api/costs/by-source")
@require_auth
async def cost_by_source():
    """Spending grouped by source label."""
    since = _parse_date(request.args.get("since"))
    until = _parse_date_end(request.args.get("until"))
    sources = db.get_cost_by_source(since=since, until=until)
    return jsonify({"sources": sources})
