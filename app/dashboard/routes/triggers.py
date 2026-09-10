"""Trigger management API — list/inspect/toggle/delete triggers and read the
firing history. Session-authenticated (the dashboard UI's Triggers tab).
Authoring happens via the triggers MCP server (the agent), not here, in v1."""

from quart import Blueprint, jsonify, request, current_app

import db
import trigger_store
from dashboard.auth import require_auth

triggers_bp = Blueprint("triggers", __name__)


def _summary(t: dict, last_fired: dict[str, float]) -> dict:
    act = t.get("action") or {}
    action_label = (f"workflow: {act.get('workflow')}" if act.get("type") == "workflow"
                    else f"prompt: {(act.get('prompt') or '')[:60]}")
    return {
        "name": t.get("name"),
        "description": t.get("description", ""),
        "source_type": (t.get("source") or {}).get("type"),
        "action": action_label,
        "sinks": t.get("sinks") or ["telegram"],
        "enabled": t.get("enabled", True),
        "debounce_seconds": t.get("debounce_seconds", 0),
        "filter": t.get("filter") or "",
        "last_fired": last_fired.get(t.get("name")),
    }


@triggers_bp.route("/api/triggers")
@require_auth
async def list_triggers():
    last = db.get_last_fired_map()
    return jsonify([_summary(t, last) for t in trigger_store.load_triggers()])


@triggers_bp.route("/api/triggers/<name>")
@require_auth
async def get_trigger(name):
    t = trigger_store.get_trigger(name)
    if not t:
        return jsonify({"error": "not found"}), 404
    out = dict(t)
    if (t.get("source") or {}).get("type") == "webhook":
        out["webhook_url"] = trigger_store.webhook_url(name)
    return jsonify(out)


@triggers_bp.route("/api/triggers/<name>/toggle", methods=["POST"])
@require_auth
async def toggle_trigger(name):
    t = trigger_store.get_trigger(name)
    if not t:
        return jsonify({"error": "not found"}), 404
    enabled = not t.get("enabled", True)
    trigger_store.set_enabled(name, enabled)
    return jsonify({"name": name, "enabled": enabled})


@triggers_bp.route("/api/triggers/<name>", methods=["DELETE"])
@require_auth
async def delete_trigger(name):
    if not trigger_store.delete_trigger(name):
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": name})


@triggers_bp.route("/api/triggers/firings")
@require_auth
async def all_firings():
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify(db.get_trigger_firings(limit=limit))


@triggers_bp.route("/api/triggers/<name>/firings")
@require_auth
async def trigger_firings(name):
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify(db.get_trigger_firings(trigger_name=name, limit=limit))


@triggers_bp.route("/api/triggers/<name>/test", methods=["POST"])
@require_auth
async def test_trigger(name):
    t = trigger_store.get_trigger(name)
    if not t:
        return jsonify({"error": "not found"}), 404
    payload = await request.get_json(silent=True) or {}
    status = current_app.trigger_engine.accept(t, payload, source="test")
    return jsonify({"status": status})
