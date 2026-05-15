"""
Agent Dashboards — serves and manages mini-dashboards built by the agent.

Dashboards live in AgentDashboards/<slug>/ with:
  - manifest.json (metadata)
  - static/index.html (frontend)
  - api.py (optional backend Blueprint)
  - data.json (optional persistence)
"""

import json
import shutil
import importlib.util
from pathlib import Path
from quart import Blueprint, request, jsonify, send_from_directory, abort

dashboards_bp = Blueprint("dashboards", __name__)

DASHBOARDS_DIR = Path(__file__).parent.parent.parent.parent / "clients" / "dashboards"
ARCHIVE_DIR = DASHBOARDS_DIR / ".archive"

# Cache of loaded API blueprints (slug -> Blueprint)
_loaded_apis: dict[str, object] = {}


def _get_dashboards(base: Path) -> list[dict]:
    """Scan a directory for dashboard projects with manifest.json."""
    dashboards = []
    if not base.exists():
        return dashboards
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        manifest_path = d / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                manifest["slug"] = d.name
                manifest["has_api"] = (d / "api.py").exists()
                manifest["has_data"] = (d / "data.json").exists()
                dashboards.append(manifest)
            except (json.JSONDecodeError, OSError):
                continue
    return dashboards


def register_dashboard_apis(app):
    """
    Scan AgentDashboards for api.py files and mount them.
    Call this during app startup and after creating new dashboards.
    """
    if not DASHBOARDS_DIR.exists():
        return

    for d in DASHBOARDS_DIR.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        api_file = d / "api.py"
        if not api_file.exists():
            continue
        if d.name in _loaded_apis:
            continue  # already loaded

        # Check if blueprint name is already registered in Quart
        bp_name = f"{d.name}-api"
        if bp_name in app.blueprints:
            _loaded_apis[d.name] = app.blueprints[bp_name]
            continue

        try:
            spec = importlib.util.spec_from_file_location(
                f"agent_dashboard_{d.name}", str(api_file)
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            if hasattr(mod, "create_blueprint"):
                bp = mod.create_blueprint(d)
                app.register_blueprint(bp, url_prefix=f"/d/{d.name}/api")
                _loaded_apis[d.name] = bp
                print(f"  [dashboards] Loaded API for '{d.name}'")
        except Exception as e:
            print(f"  [dashboards] Failed to load API for '{d.name}': {e}")


# ── Management API ──────────────────────────────────────────────

@dashboards_bp.route("/api/dashboards", methods=["GET"])
async def list_dashboards():
    active = _get_dashboards(DASHBOARDS_DIR)
    archived = _get_dashboards(ARCHIVE_DIR)
    for d in archived:
        d["archived"] = True
    return jsonify({"active": active, "archived": archived})


@dashboards_bp.route("/api/dashboards/<slug>", methods=["DELETE"])
async def delete_dashboard(slug: str):
    """Archive a dashboard (soft delete)."""
    src = DASHBOARDS_DIR / slug
    if not src.exists() or not (src / "manifest.json").exists():
        return jsonify({"error": "not found"}), 404

    ARCHIVE_DIR.mkdir(exist_ok=True)
    dest = ARCHIVE_DIR / slug
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(src), str(dest))

    # Remove from loaded APIs cache
    _loaded_apis.pop(slug, None)

    return jsonify({"ok": True, "action": "archived"})


@dashboards_bp.route("/api/dashboards/<slug>/restore", methods=["POST"])
async def restore_dashboard(slug: str):
    """Restore an archived dashboard."""
    src = ARCHIVE_DIR / slug
    if not src.exists():
        return jsonify({"error": "not found in archive"}), 404

    dest = DASHBOARDS_DIR / slug
    if dest.exists():
        return jsonify({"error": "active dashboard with same name exists"}), 409

    shutil.move(str(src), str(dest))

    # Load API blueprint if the restored dashboard has one
    from quart import current_app
    register_dashboard_apis(current_app)

    return jsonify({"ok": True, "action": "restored"})


@dashboards_bp.route("/api/dashboards/reload", methods=["POST"])
async def reload_dashboards():
    """Re-scan and load any new dashboard API blueprints."""
    from quart import current_app
    register_dashboard_apis(current_app)
    return jsonify({"ok": True})


# ── Static file serving ─────────────────────────────────────────

@dashboards_bp.route("/d/<slug>/")
async def serve_dashboard(slug: str):
    """Serve a dashboard's index.html."""
    static_dir = DASHBOARDS_DIR / slug / "static"
    if not static_dir.exists():
        abort(404)
    return await send_from_directory(str(static_dir), "index.html")


@dashboards_bp.route("/d/<slug>/<path:filename>")
async def serve_dashboard_static(slug: str, filename: str):
    """Serve static assets for a dashboard."""
    static_dir = DASHBOARDS_DIR / slug / "static"
    if not static_dir.exists():
        abort(404)
    return await send_from_directory(str(static_dir), filename)
