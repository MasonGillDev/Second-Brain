"""Toolbus — the dashboard's running ToolRouter exposed over loopback HTTP.

The dashboard is the sole process that spawns MCP server subprocesses. Every
other service (telegram bot, scheduler) runs a RemoteToolRouter
(skills/remote_router.py) that discovers and calls tools through these two
endpoints, so exactly one instance of each MCP server ever exists — no more
sibling light/music/tv servers racing each other or the Cync cloud evicting
the second session.

Authenticated with the same local 'watch-api-key' bearer token as the lights
REST API.
"""

import hmac

from quart import Blueprint, request, jsonify, current_app
from keychain import get_secret

toolbus_bp = Blueprint("toolbus", __name__)


def _check_auth() -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return "unauthorized"
    token = auth[7:]
    try:
        correct = get_secret("watch-api-key")
    except RuntimeError:
        return "watch-api-key not configured"
    if not hmac.compare_digest(token, correct):
        return "unauthorized"
    return None


@toolbus_bp.route("/api/toolbus/tools", methods=["GET"])
async def toolbus_tools():
    """Every discovered tool (namespaced name, description, input_schema).

    The TOOL_ALLOWLIST was already applied at discovery; skill gating is the
    caller's concern (RemoteToolRouter inherits it), so the full list goes out.
    """
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    return jsonify({"tools": current_app.agent.router._tools})


@toolbus_bp.route("/api/toolbus/call", methods=["POST"])
async def toolbus_call():
    """Call one tool by namespaced name and return its string result.

    router.call_tool never raises — failures come back as '[ERROR] ...' strings,
    which is exactly what the remote agent's tool loop expects to see.
    """
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    data = await request.get_json()
    name = (data or {}).get("name", "")
    arguments = (data or {}).get("arguments") or {}
    if not name:
        return jsonify({"error": "missing tool name"}), 400
    result = await current_app.agent.router.call_tool(name, arguments)
    return jsonify({"result": result})
