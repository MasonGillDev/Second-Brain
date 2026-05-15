"""Tool management endpoints."""

import config
from quart import Blueprint, jsonify, current_app
from dashboard.auth import require_auth

tools_bp = Blueprint("tools", __name__)


@tools_bp.route("/api/tools")
@require_auth
async def list_tools():
    router = current_app.agent.router
    servers = {}

    for name, client in router._clients.items():
        server_tools = [
            t["name"].split("__", 1)[1]
            for t in router._tools
            if t["name"].startswith(name + "__")
        ]
        servers[name] = {
            "tools": server_tools,
            "enabled": name not in router.disabled_servers,
            "description": config.SKILL_MANIFEST.get(name, ""),
        }

    return jsonify({"servers": servers})


@tools_bp.route("/api/tools/<server>/toggle", methods=["POST"])
@require_auth
async def toggle_server(server):
    router = current_app.agent.router

    if server not in router._clients:
        return jsonify({"error": "unknown server"}), 404

    if server in router.disabled_servers:
        router.disabled_servers.discard(server)
        enabled = True
    else:
        router.disabled_servers.add(server)
        enabled = False

    return jsonify({"server": server, "enabled": enabled})
