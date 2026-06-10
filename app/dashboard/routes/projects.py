"""Project tracking toolkit — dashboard JSON API.

Thin CRUD over project_store plus the on-demand context bundle from
project_context. Endpoints are namespaced under /api/projects/... (no collision
with the scheduled-tasks /api/tasks route). Network-bound endpoints (context,
push-to-github) run off the event loop via asyncio.to_thread.
"""

import asyncio

from quart import Blueprint, request, jsonify, current_app
from dashboard.auth import require_auth

import project_store as store
import project_context as pctx
import project_index as pidx

projects_bp = Blueprint("projects", __name__)


# ---- Projects ----

@projects_bp.route("/api/projects")
@require_auth
async def list_projects():
    return jsonify({"projects": store.list_projects()})


@projects_bp.route("/api/projects", methods=["POST"])
@require_auth
async def create_project():
    data = await request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    try:
        p = store.create_project(
            name=name,
            github_repo=data.get("github_repo", ""),
            dev_machine=data.get("dev_machine", ""),
            path=data.get("path", ""),
            similar_projects=data.get("similar_projects", ""),
            docs_path=data.get("docs_path", ""),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(p), 201


@projects_bp.route("/api/projects/<int:pid>")
@require_auth
async def get_project(pid):
    p = store.get_project(pid)
    if p is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"project": p, "tasks": store.list_tasks(pid), "notes": store.list_notes(pid)})


@projects_bp.route("/api/projects/<int:pid>", methods=["PUT"])
@require_auth
async def update_project(pid):
    data = await request.get_json() or {}
    p = store.update_project(pid, **{k: data[k] for k in data if k in store._PROJECT_FIELDS})
    if p is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(p)


@projects_bp.route("/api/projects/<int:pid>", methods=["DELETE"])
@require_auth
async def delete_project(pid):
    ok = store.delete_project(pid)
    if ok:
        try:  # best-effort: drop the project's chunks from the search index
            await asyncio.to_thread(pidx.remove_project, pid, current_app.vector_store)
        except Exception:
            pass
    return jsonify({"status": "deleted" if ok else "not found"})


# ---- Tasks ----

@projects_bp.route("/api/projects/<int:pid>/tasks")
@require_auth
async def list_tasks(pid):
    return jsonify({"tasks": store.list_tasks(pid, request.args.get("status") or None)})


@projects_bp.route("/api/projects/<int:pid>/tasks", methods=["POST"])
@require_auth
async def create_task(pid):
    data = await request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    priority = data.get("priority", "med")
    if priority not in store.VALID_PRIORITIES:
        return jsonify({"error": f"priority must be one of {store.VALID_PRIORITIES}"}), 400
    t = store.create_task(pid, name, data.get("description", ""), priority)
    if t is None:
        return jsonify({"error": "project not found"}), 404
    return jsonify(t), 201


@projects_bp.route("/api/projects/tasks/<int:tid>", methods=["PUT"])
@require_auth
async def update_task(tid):
    data = await request.get_json() or {}
    if data.get("status") and data["status"] not in store.VALID_STATUSES:
        return jsonify({"error": f"status must be one of {store.VALID_STATUSES}"}), 400
    if data.get("priority") and data["priority"] not in store.VALID_PRIORITIES:
        return jsonify({"error": f"priority must be one of {store.VALID_PRIORITIES}"}), 400
    t = store.update_task(tid, **{k: data[k] for k in data if k in store._TASK_FIELDS})
    if t is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(t)


@projects_bp.route("/api/projects/tasks/<int:tid>", methods=["DELETE"])
@require_auth
async def delete_task(tid):
    return jsonify({"status": "deleted" if store.delete_task(tid) else "not found"})


@projects_bp.route("/api/projects/tasks/<int:tid>/push-github", methods=["POST"])
@require_auth
async def push_task_to_github(tid):
    t = store.get_task(tid)
    if t is None:
        return jsonify({"error": "task not found"}), 404
    if t.get("github_issue"):
        return jsonify({"error": f"already linked to {t['github_issue']}"}), 400
    p = store.get_project(t["project_id"])
    try:
        issue = await asyncio.to_thread(
            pctx.create_github_issue, p.get("github_repo", ""), t["name"], t.get("description", ""))
    except pctx.ToolGateError as e:
        return jsonify({"error": str(e)}), 400
    ref = issue.get("html_url") or (f"#{issue['number']}" if issue.get("number") else "(created)")
    updated = store.update_task(tid, github_issue=ref)
    return jsonify({"task": updated, "issue": issue})


# ---- Notes ----

@projects_bp.route("/api/projects/<int:pid>/notes")
@require_auth
async def list_notes(pid):
    return jsonify({"notes": store.list_notes(pid)})


@projects_bp.route("/api/projects/<int:pid>/notes", methods=["POST"])
@require_auth
async def create_note(pid):
    data = await request.get_json() or {}
    n = store.create_note(pid, data.get("name", ""), data.get("description", ""))
    if n is None:
        return jsonify({"error": "project not found"}), 404
    return jsonify(n), 201


@projects_bp.route("/api/projects/notes/<int:nid>", methods=["PUT"])
@require_auth
async def update_note(nid):
    data = await request.get_json() or {}
    n = store.update_note(nid, **{k: data[k] for k in data if k in store._NOTE_FIELDS})
    if n is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(n)


@projects_bp.route("/api/projects/notes/<int:nid>", methods=["DELETE"])
@require_auth
async def delete_note(nid):
    return jsonify({"status": "deleted" if store.delete_note(nid) else "not found"})


# ---- Docs ----

@projects_bp.route("/api/projects/<int:pid>/docs")
@require_auth
async def list_docs(pid):
    p = store.get_project(pid)
    if p is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"docs_path": p.get("docs_path", ""), "docs": pctx.list_docs(p.get("docs_path", ""))})


@projects_bp.route("/api/projects/<int:pid>/docs/<path:filename>")
@require_auth
async def get_doc(pid, filename):
    p = store.get_project(pid)
    if p is None:
        return jsonify({"error": "not found"}), 404
    try:
        text = await asyncio.to_thread(pctx.read_doc, p.get("docs_path", ""), filename)
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"filename": filename, "text": text})


# ---- Context (on-demand aggregation) ----

@projects_bp.route("/api/projects/<int:pid>/context")
@require_auth
async def project_context(pid):
    if store.get_project(pid) is None:
        return jsonify({"error": "not found"}), 404
    ctx = await asyncio.to_thread(pctx.gather_context, pid)
    return jsonify({"context": ctx, "text": pctx.format_context(ctx)})


# ---- Knowledge search / reindex ----

@projects_bp.route("/api/projects/<int:pid>/search")
@require_auth
async def search_project(pid):
    if store.get_project(pid) is None:
        return jsonify({"error": "not found"}), 404
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"results": []})
    st = request.args.get("type") or None
    try:
        results = await asyncio.to_thread(pidx.search_project, pid, q, st, 10, current_app.vector_store)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"search unavailable: {e}"}), 503
    return jsonify({"results": results})


@projects_bp.route("/api/projects/<int:pid>/reindex", methods=["POST"])
@require_auth
async def reindex_project(pid):
    if store.get_project(pid) is None:
        return jsonify({"error": "not found"}), 404
    try:
        counts = await asyncio.to_thread(pidx.reindex_project, pid, True, current_app.vector_store)
    except Exception as e:
        return jsonify({"error": f"reindex failed: {e}"}), 503
    return jsonify({"counts": counts})
