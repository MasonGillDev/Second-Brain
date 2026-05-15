"""REST API for light control — used by the iPad app."""

import re
import hmac
from quart import Blueprint, request, jsonify, current_app
from keychain import get_secret

_LIGHT_RE = re.compile(
    r'\[(?P<id>[^\]]+)\]\s+(?P<name>.+?)\s+\u2014\s+(?P<on>ON|OFF),\s+'
    r'(?P<brightness>\d+)%\s+brightness\s+\((?P<reachable>reachable|UNREACHABLE)\)'
)
_ROOM_RE = re.compile(
    r'\[(?P<id>[^\]]+)\]\s+(?P<name>.+?)\s+\((?P<type>[^)]+)\)\s+\u2014\s+(?P<on>ON|OFF),\s+'
    r'(?P<brightness>\d+)%,\s+(?P<light_count>\d+)\s+lights'
)
_SCENE_RE = re.compile(
    r'\[(?P<id>[^\]]+)\]\s+(?P<name>.+?)\s+\(group\s+(?P<group>[^)]+)\)'
)


def _parse_lights(raw: str) -> list[dict]:
    lights = []
    for line in raw.strip().split("\n"):
        m = _LIGHT_RE.match(line.strip())
        if m:
            lights.append({
                "id": m.group("id"),
                "name": m.group("name"),
                "on": m.group("on") == "ON",
                "brightness": int(m.group("brightness")),
                "reachable": m.group("reachable") == "reachable",
            })
    return lights


def _parse_rooms(raw: str) -> list[dict]:
    rooms = []
    for line in raw.strip().split("\n"):
        m = _ROOM_RE.match(line.strip())
        if m:
            rooms.append({
                "id": m.group("id"),
                "name": m.group("name"),
                "type": m.group("type"),
                "on": m.group("on") == "ON",
                "brightness": int(m.group("brightness")),
                "light_count": int(m.group("light_count")),
            })
    return rooms


def _parse_scenes(raw: str) -> list[dict]:
    scenes = []
    for line in raw.strip().split("\n"):
        m = _SCENE_RE.match(line.strip())
        if m:
            scenes.append({
                "id": m.group("id"),
                "name": m.group("name"),
                "group": m.group("group"),
            })
    return scenes

lights_bp = Blueprint("lights", __name__)


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


async def _call_light_tool(tool_name: str, arguments: dict) -> str:
    router = current_app.agent.router
    return await router.call_tool(f"lights__{tool_name}", arguments)


@lights_bp.route("/api/lights", methods=["GET"])
async def get_lights():
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    result = await _call_light_tool("list_lights", {})
    return jsonify({"lights": _parse_lights(result)})


@lights_bp.route("/api/lights/rooms", methods=["GET"])
async def get_rooms():
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    result = await _call_light_tool("list_rooms", {})
    return jsonify({"rooms": _parse_rooms(result)})


@lights_bp.route("/api/lights/scenes", methods=["GET"])
async def get_scenes():
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    result = await _call_light_tool("list_scenes", {})
    return jsonify({"scenes": _parse_scenes(result)})


@lights_bp.route("/api/lights/<light_id>", methods=["PUT"])
async def set_light(light_id: str):
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    data = await request.get_json()
    if not data:
        return jsonify({"error": "missing body"}), 400
    args = {"light_id": light_id}
    if "on" in data:
        args["on"] = data["on"]
    if "brightness" in data:
        args["brightness"] = data["brightness"]
    if "color" in data:
        args["color"] = data["color"]
    if "color_temp" in data:
        args["color_temp"] = data["color_temp"]
    result = await _call_light_tool("set_light", args)
    return jsonify({"result": result})


@lights_bp.route("/api/lights/room/<room_name>", methods=["PUT"])
async def set_room(room_name: str):
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    data = await request.get_json()
    if not data:
        return jsonify({"error": "missing body"}), 400
    args = {"room_name": room_name}
    if "on" in data:
        args["on"] = data["on"]
    if "brightness" in data:
        args["brightness"] = data["brightness"]
    if "color" in data:
        args["color"] = data["color"]
    if "color_temp" in data:
        args["color_temp"] = data["color_temp"]
    result = await _call_light_tool("set_room", args)
    return jsonify({"result": result})


@lights_bp.route("/api/lights/all", methods=["PUT"])
async def set_all():
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    data = await request.get_json()
    if not data:
        return jsonify({"error": "missing body"}), 400
    args = {}
    if "on" in data:
        args["on"] = data["on"]
    if "brightness" in data:
        args["brightness"] = data["brightness"]
    if "color" in data:
        args["color"] = data["color"]
    if "color_temp" in data:
        args["color_temp"] = data["color_temp"]
    result = await _call_light_tool("set_all_lights", args)
    return jsonify({"result": result})


@lights_bp.route("/api/lights/scene", methods=["POST"])
async def activate_scene():
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401
    data = await request.get_json()
    if not data or not data.get("scene_name"):
        return jsonify({"error": "missing scene_name"}), 400
    result = await _call_light_tool("activate_scene", {"scene_name": data["scene_name"]})
    return jsonify({"result": result})
