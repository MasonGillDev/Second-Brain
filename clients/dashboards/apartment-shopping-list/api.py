"""Backend API for Apartment Shopping List."""

import json
import uuid
from pathlib import Path
from quart import Blueprint, request, jsonify


def create_blueprint(data_dir: Path) -> Blueprint:
    bp = Blueprint("apartment-shopping-list-api", __name__)
    data_file = data_dir / "data.json"

    def _load() -> dict:
        if data_file.exists():
            return json.loads(data_file.read_text())
        return {"items": []}

    def _save(data: dict):
        data_file.write_text(json.dumps(data, indent=2))

    @bp.route("/items", methods=["GET"])
    async def get_items():
        return jsonify(_load().get("items", []))

    @bp.route("/items", methods=["POST"])
    async def add_item():
        body = await request.get_json()
        if not body or not body.get("name", "").strip():
            return jsonify({"error": "name is required"}), 400
        item = {
            "id": str(uuid.uuid4()),
            "name": body["name"].strip(),
            "category": body.get("category", "").strip(),
            "bought": False,
        }
        data = _load()
        data.setdefault("items", []).append(item)
        _save(data)
        return jsonify(item), 201

    @bp.route("/items/<item_id>", methods=["PATCH"])
    async def update_item(item_id):
        body = await request.get_json()
        data = _load()
        for item in data.get("items", []):
            if item["id"] == item_id:
                if "bought" in body:
                    item["bought"] = bool(body["bought"])
                if "name" in body:
                    item["name"] = body["name"].strip()
                if "category" in body:
                    item["category"] = body["category"].strip()
                _save(data)
                return jsonify(item)
        return jsonify({"error": "not found"}), 404

    @bp.route("/items/<item_id>", methods=["DELETE"])
    async def delete_item(item_id):
        data = _load()
        items = data.get("items", [])
        data["items"] = [i for i in items if i["id"] != item_id]
        _save(data)
        return jsonify({"ok": True})

    return bp
