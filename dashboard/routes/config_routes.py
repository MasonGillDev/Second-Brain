"""Config viewer/editor endpoints."""

import json
import os
import config
from quart import Blueprint, request, jsonify
from dashboard.auth import require_auth

config_bp = Blueprint("config", __name__)

OVERRIDES_FILE = "./memory/data/config_overrides.json"

# Keys that should not be editable at runtime
READONLY_KEYS = {
    "MCP_SERVERS", "LLM_PROVIDER", "CHROMA_PERSIST_DIR",
    "TOOL_ALLOWLIST", "ALWAYS_INCLUDE_SERVERS", "SKILL_MANIFEST",
    "SESSION_FILE", "DOCS_DIR",
}

# Type hints for the config editor
TYPE_MAP = {
    bool: "boolean",
    int: "number",
    float: "number",
    str: "string",
}


@config_bp.route("/api/config")
@require_auth
async def get_config():
    values = {}
    for key in sorted(dir(config)):
        if not key.isupper() or key.startswith("_"):
            continue
        val = getattr(config, key)
        val_type = TYPE_MAP.get(type(val))
        if val_type is None:
            continue  # Skip non-serializable (dicts, lists, etc.)
        values[key] = {
            "value": val,
            "type": val_type,
            "readonly": key in READONLY_KEYS,
        }
    return jsonify({"config": values})


@config_bp.route("/api/config", methods=["PUT"])
@require_auth
async def update_config():
    data = await request.get_json()
    updates = data.get("updates", {})

    if not updates:
        return jsonify({"error": "no updates provided"}), 400

    # Validate
    for key in updates:
        if key in READONLY_KEYS:
            return jsonify({"error": f"'{key}' is read-only"}), 400
        if not hasattr(config, key):
            return jsonify({"error": f"unknown config key '{key}'"}), 400

    # Load existing overrides
    overrides = {}
    if os.path.exists(OVERRIDES_FILE):
        with open(OVERRIDES_FILE) as f:
            overrides = json.load(f)

    # Apply
    for key, value in updates.items():
        overrides[key] = value
        setattr(config, key, value)

    # Save
    os.makedirs(os.path.dirname(OVERRIDES_FILE), exist_ok=True)
    with open(OVERRIDES_FILE, "w") as f:
        json.dump(overrides, f, indent=2)

    return jsonify({"status": "updated", "applied": list(updates.keys())})
