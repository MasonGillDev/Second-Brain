"""Workflow builder endpoints — CRUD, tool palette, and in-process test runs.

Thin wrappers over workflow_store (definitions) and workflow_runner (execution).
The tool palette is derived from the live brain's router so the builder always
offers exactly the tools that are actually loaded. Test runs execute the
workflow FOR REAL in-process (tools have real side effects) and return the final
output plus a per-step trace, so a broken step is obvious.
"""

import asyncio
import json

import config
import workflow_store as store
import workflow_runner as runner
from quart import Blueprint, request, jsonify, current_app, Response
from dashboard.auth import require_auth

workflows_bp = Blueprint("workflows", __name__)


def _summary(w: dict) -> dict:
    """Compact record for the list view."""
    return {
        "name": w.get("name"),
        "description": w.get("description", ""),
        "steps": len(w.get("steps", [])),
        "params": [p.get("name") for p in (w.get("params") or [])],
        "surfaces": w.get("surfaces") or {},
    }


@workflows_bp.route("/api/workflows")
@require_auth
async def list_workflows():
    return jsonify({"workflows": [_summary(w) for w in store.load_workflows()]})


@workflows_bp.route("/api/workflows/<name>")
@require_auth
async def get_workflow(name):
    w = store.get_workflow(name)
    if not w:
        return jsonify({"error": "not found"}), 404
    return jsonify(w)


@workflows_bp.route("/api/workflows", methods=["POST"])
@require_auth
async def upsert_workflow():
    defn = await request.get_json()
    if not isinstance(defn, dict):
        return jsonify({"error": "body must be a workflow object"}), 400
    errs = store.validate_workflow(defn)
    if errs:
        return jsonify({"error": "; ".join(errs), "errors": errs}), 400
    # to_thread: upsert may make a short LLM call (trigger generation) + resync
    # the embedding index — don't block the event loop on it.
    action = await asyncio.to_thread(store.upsert_workflow, defn)
    return jsonify({"ok": True, "action": action, "name": defn["name"],
                    "triggers": defn.get("triggers") or []})


@workflows_bp.route("/api/workflows/<name>", methods=["DELETE"])
@require_auth
async def delete_workflow(name):
    return jsonify({"ok": store.delete_workflow(name)})


@workflows_bp.route("/api/workflows/palette")
@require_auth
async def palette():
    """Tools available as step nodes, grouped by server, each with its args
    derived from the tool's input_schema. Plus existing workflow names (for the
    composition node)."""
    router = current_app.agent.router
    servers: dict[str, dict] = {}
    for t in router._tools:
        server, _, tool = t["name"].partition("__")
        if server == "workflows":
            continue  # management tools aren't steps — use the Workflow node instead
        schema = t.get("input_schema") or {}
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        params = [{
            "name": pn,
            "type": (pdef.get("type") or "string") if isinstance(pdef, dict) else "string",
            "required": pn in required,
            "description": pdef.get("description", "") if isinstance(pdef, dict) else "",
        } for pn, pdef in props.items()]
        servers.setdefault(server, {
            "description": config.SKILL_MANIFEST.get(server, ""),
            "tools": [],
        })["tools"].append({
            "name": tool,
            "full_name": t["name"],
            "description": t.get("description", ""),
            "params": params,
        })
    workflows = [w["name"] for w in store.load_workflows()]
    return jsonify({"servers": servers, "workflows": workflows})


_MODELS_CACHE: list | None = None


@workflows_bp.route("/api/workflows/models")
@require_auth
async def models():
    """OpenRouter model list for the per-step model picker (id + name), cached for
    the process lifetime. Falls back to just the default on any failure."""
    global _MODELS_CACHE
    if _MODELS_CACHE is None:
        _MODELS_CACHE = []
        try:
            import httpx
            headers = {}
            try:
                from keychain import get_secret
                key = get_secret("openrouter-api-key")
                if key:
                    headers["Authorization"] = f"Bearer {key}"
            except Exception:
                pass
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                r.raise_for_status()
                data = r.json().get("data", [])
            _MODELS_CACHE = sorted(
                ({"id": m["id"], "name": m.get("name") or m["id"]} for m in data if m.get("id")),
                key=lambda m: m["name"].lower(),
            )
        except Exception as e:
            print(f"  [workflows] model list fetch failed: {e}")
    return jsonify({"default": config.MODEL, "models": _MODELS_CACHE})


@workflows_bp.route("/api/workflows/test", methods=["POST"])
@require_auth
async def test_workflow():
    """Run a (possibly unsaved) definition and return output + per-step trace.
    Executes tools for real."""
    data = await request.get_json() or {}
    defn = data.get("definition")
    params = data.get("params") or {}
    if not isinstance(defn, dict):
        return jsonify({"error": "definition (object) required"}), 400
    errs = store.validate_workflow(defn)
    if errs:
        return jsonify({"error": "; ".join(errs), "errors": errs}), 400

    # Stream live progress as Server-Sent Events: a "start" event per step (so the
    # UI can show which step is running), then a final "result" event.
    async def stream():
        queue: asyncio.Queue = asyncio.Queue()
        result: dict = {}

        async def run():
            trace: list = []
            try:
                out = await asyncio.wait_for(
                    runner.run_workflow(defn, params, trace=trace,
                                        on_event=queue.put_nowait), timeout=120)
                result.update({"output": out, "trace": trace})
            except asyncio.TimeoutError:
                result.update({"error": ("Timed out after 120s. A prompt step is likely "
                               "looping — make sure it references the previous step "
                               "(e.g. {{step1}})."), "trace": trace})
            except runner.WorkflowError as e:
                result.update({"error": str(e), "trace": trace})
            except Exception as e:
                result.update({"error": f"{type(e).__name__}: {e}", "trace": trace})
            queue.put_nowait({"type": "__done__"})

        task = asyncio.ensure_future(run())
        while True:
            ev = await queue.get()
            if ev.get("type") == "__done__":
                break
            yield f"data: {json.dumps(ev)}\n\n"
        yield f"data: {json.dumps({'type': 'result', **result})}\n\n"
        await task

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
