# AgentDashboards — Conventions

You are building a mini-dashboard that will be served by a shared Flask/Quart server.
Follow these conventions exactly.

## Directory Structure

Each dashboard lives in its own folder under `AgentDashboards/`:

```
AgentDashboards/<project-slug>/
  manifest.json       # REQUIRED — metadata
  static/
    index.html        # REQUIRED — the main page
    style.css         # optional
    app.js            # optional
    ...               # any other static assets
  api.py              # optional — Python backend (Flask Blueprint)
  data.json           # optional — simple JSON persistence
```

## manifest.json

```json
{
  "name": "Human-Readable Name",
  "description": "What this dashboard does",
  "icon": "chart-bar",
  "created_at": "2026-05-07T12:00:00Z"
}
```

- `icon` is optional. Use a descriptive keyword (displayed as text if no icon library).
- `created_at` should be ISO 8601.

## Frontend (static/index.html)

- Must be a self-contained HTML file (inline CSS/JS is fine, or reference sibling files).
- The page is served at `/d/<project-slug>/` — all asset references should be relative.
- For API calls to the dashboard's own backend, use relative paths: `fetch('api/endpoint')`.
- For API calls to the main Second Brain dashboard, use absolute paths: `fetch('/api/chat')`.
- Make it responsive. Dark mode support is a plus (check `prefers-color-scheme`).
- Use modern, clean design. No heavy frameworks needed — vanilla JS is preferred.

## Backend API (api.py) — Optional

If the dashboard needs server-side logic, create `api.py` with this exact pattern:

```python
"""Backend API for <dashboard-name>."""

import json
from pathlib import Path
from quart import Blueprint, request, jsonify

def create_blueprint(data_dir: Path) -> Blueprint:
    """
    Factory that returns a Blueprint for this dashboard.

    Args:
        data_dir: Path to this dashboard's directory (for reading/writing data.json).
    """
    bp = Blueprint("<project-slug>-api", __name__)
    data_file = data_dir / "data.json"

    def _load_data() -> dict:
        if data_file.exists():
            return json.loads(data_file.read_text())
        return {}

    def _save_data(data: dict):
        data_file.write_text(json.dumps(data, indent=2))

    @bp.route("/items", methods=["GET"])
    async def get_items():
        data = _load_data()
        return jsonify(data.get("items", []))

    @bp.route("/items", methods=["POST"])
    async def add_item():
        body = await request.get_json()
        data = _load_data()
        data.setdefault("items", []).append(body)
        _save_data(data)
        return jsonify({"ok": True})

    return bp
```

Key rules:
- Export a `create_blueprint(data_dir: Path) -> Blueprint` function.
- Blueprint name must be unique (use `<project-slug>-api`).
- Use `data.json` for persistence — read/write via the `data_dir` path.
- All routes are relative (no leading `/d/<slug>/api/` — the server mounts them).
- Use async route handlers (Quart, not Flask).
- Do NOT import anything from the Second Brain codebase.

## data.json — Optional

Simple JSON file for persistence. The backend reads/writes it. Structure is up to you.
If no backend is needed but you want to store state, the frontend can use localStorage.

## Important Rules

1. Do NOT modify any files outside this dashboard's directory.
2. Do NOT install Python packages — use only stdlib + what Quart provides.
3. For JS dependencies, use CDN links (e.g., Chart.js, D3, etc.).
4. Keep it simple. One dashboard = one purpose.
5. The slug (directory name) should be lowercase-kebab-case.
