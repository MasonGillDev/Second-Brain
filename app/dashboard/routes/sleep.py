"""Sleep agent trigger and log viewer."""

import os
import asyncio
from quart import Blueprint, request, jsonify, current_app
from dashboard.auth import require_auth

sleep_bp = Blueprint("sleep", __name__)

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "memory", "data", "sleep_logs")


@sleep_bp.route("/api/sleep/run", methods=["POST"])
@require_auth
async def run_sleep():
    if current_app.sleep_running:
        return jsonify({"error": "sleep agent already running"}), 409

    data = await request.get_json() or {}
    dry_run = data.get("dry_run", False)

    current_app.sleep_running = True

    async def _run():
        try:
            from interfaces.sleep import run_sleep_cycle
            await asyncio.to_thread(run_sleep_cycle, dry_run=dry_run)
        except Exception as e:
            print(f"  [sleep] Error: {e}")
        finally:
            current_app.sleep_running = False

    asyncio.create_task(_run())
    return jsonify({"status": "started", "dry_run": dry_run})


@sleep_bp.route("/api/sleep/status")
@require_auth
async def sleep_status():
    return jsonify({"running": current_app.sleep_running})


@sleep_bp.route("/api/sleep/logs")
@require_auth
async def list_logs():
    if not os.path.exists(LOG_DIR):
        return jsonify({"logs": []})

    def _list():
        return sorted(
            [f for f in os.listdir(LOG_DIR) if f.endswith(".log")],
            reverse=True,
        )
    files = await asyncio.to_thread(_list)
    return jsonify({"logs": files})


@sleep_bp.route("/api/sleep/logs/<filename>")
@require_auth
async def get_log(filename):
    # Prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "invalid filename"}), 400

    path = os.path.join(LOG_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404

    with open(path) as f:
        content = f.read()

    return jsonify({"filename": filename, "content": content})
