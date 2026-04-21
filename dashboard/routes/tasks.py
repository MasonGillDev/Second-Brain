"""Scheduled tasks CRUD endpoints."""

import json
import os
import uuid
from datetime import datetime
from quart import Blueprint, request, jsonify
from dashboard.auth import require_auth

tasks_bp = Blueprint("tasks", __name__)

TASKS_FILE = "./memory/data/scheduled_tasks.json"


def _load():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE) as f:
        return json.load(f)


def _save(tasks):
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


@tasks_bp.route("/api/tasks")
@require_auth
async def list_tasks():
    return jsonify({"tasks": _load()})


@tasks_bp.route("/api/tasks", methods=["POST"])
@require_auth
async def create_task():
    data = await request.get_json()
    name = data.get("name", "").strip()
    prompt = data.get("prompt", "").strip()
    schedule = data.get("schedule", "").strip()

    if not all([name, prompt, schedule]):
        return jsonify({"error": "name, prompt, and schedule required"}), 400

    tasks = _load()
    task = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "prompt": prompt,
        "schedule": schedule,
        "enabled": True,
        "created_at": datetime.now().isoformat(),
        "last_run": None,
    }
    tasks.append(task)
    _save(tasks)
    return jsonify(task), 201


@tasks_bp.route("/api/tasks/<task_id>", methods=["PUT"])
@require_auth
async def update_task(task_id):
    data = await request.get_json()
    tasks = _load()

    for task in tasks:
        if task["id"] == task_id:
            for key in ("name", "prompt", "schedule", "enabled"):
                if key in data:
                    task[key] = data[key]
            _save(tasks)
            return jsonify(task)

    return jsonify({"error": "not found"}), 404


@tasks_bp.route("/api/tasks/<task_id>", methods=["DELETE"])
@require_auth
async def delete_task(task_id):
    tasks = _load()
    tasks = [t for t in tasks if t["id"] != task_id]
    _save(tasks)
    return jsonify({"status": "deleted"})


@tasks_bp.route("/api/tasks/<task_id>/toggle", methods=["POST"])
@require_auth
async def toggle_task(task_id):
    tasks = _load()
    for task in tasks:
        if task["id"] == task_id:
            task["enabled"] = not task["enabled"]
            _save(tasks)
            return jsonify(task)
    return jsonify({"error": "not found"}), 404
