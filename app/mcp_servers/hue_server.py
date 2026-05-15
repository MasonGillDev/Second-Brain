"""
Philips Hue MCP Server.

Controls Hue lights via the local bridge REST API.
Bridge API key stored in macOS Keychain as "hue-api-key".
"""

import sys
import os
import json
import subprocess
import urllib.request
import urllib.error
import ssl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from keychain import get_secret

mcp = FastMCP("lights")

BRIDGE_IP = "192.168.1.65"
API_KEY = get_secret("hue-api-key")
BASE_URL = f"https://{BRIDGE_IP}/api/{API_KEY}"

# Hue bridge uses a self-signed cert — skip verification for local API
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _request(path: str, method: str = "GET", body: dict | None = None) -> dict | list:
    """Make a request to the Hue Bridge API."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        return {"error": f"Bridge unreachable: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ---- Discovery tools ----

@mcp.tool()
def list_lights() -> str:
    """
    List all lights connected to the Hue Bridge with their current state.
    Shows: name, on/off, brightness percentage, and reachability.
    """
    lights = _request("/lights")
    if isinstance(lights, dict) and "error" in lights:
        return lights["error"]

    lines = []
    for id, light in sorted(lights.items(), key=lambda x: int(x[0])):
        state = light["state"]
        on = "ON" if state["on"] else "OFF"
        bri = int(state["bri"] / 254 * 100)
        reachable = "reachable" if state["reachable"] else "UNREACHABLE"
        lines.append(f"[{id}] {light['name']} — {on}, {bri}% brightness ({reachable})")

    return "\n".join(lines) if lines else "No lights found."


@mcp.tool()
def list_rooms() -> str:
    """
    List all rooms/groups with their lights and current state.
    """
    groups = _request("/groups")
    if isinstance(groups, dict) and "error" in groups:
        return groups["error"]

    lines = []
    for id, group in sorted(groups.items(), key=lambda x: int(x[0])):
        action = group.get("action", {})
        on = "ON" if action.get("on") else "OFF"
        bri = int(action.get("bri", 0) / 254 * 100)
        light_count = len(group.get("lights", []))
        lines.append(f"[{id}] {group['name']} ({group.get('type', 'Group')}) — {on}, {bri}%, {light_count} lights")

    return "\n".join(lines) if lines else "No rooms/groups found."


@mcp.tool()
def list_scenes() -> str:
    """
    List all saved scenes. Scenes are preconfigured light states
    that can be activated to set mood/ambiance.
    """
    scenes = _request("/scenes")
    if isinstance(scenes, dict) and "error" in scenes:
        return scenes["error"]

    lines = []
    for id, scene in scenes.items():
        group = scene.get("group", "?")
        lines.append(f"[{id}] {scene['name']} (group {group})")

    return "\n".join(lines) if lines else "No scenes found."


# ---- Control tools ----

@mcp.tool()
def set_light(light_id: str, on: bool | None = None, brightness: int | None = None,
              color: str | None = None, color_temp: str | None = None) -> str:
    """
    Control a specific light.

    Args:
        light_id: The light ID (from list_lights).
        on: Turn on (true) or off (false). Omit to keep current state.
        brightness: 0-100 percentage. Omit to keep current brightness.
        color: Color name ("red", "blue", "green", "purple", "orange", "pink",
               "yellow", "white") or hex color ("#FF0000"). Omit for no change.
        color_temp: Color temperature preset: "warm", "cool", "daylight",
                    "candlelight", "sunset". Omit for no change.
    """
    state = _build_state(on, brightness, color, color_temp)
    if not state:
        return "No changes specified."

    result = _request(f"/lights/{light_id}/state", method="PUT", body=state)
    return _format_result(result)


@mcp.tool()
def set_room(room_name: str, on: bool | None = None, brightness: int | None = None,
             color: str | None = None, color_temp: str | None = None) -> str:
    """
    Control all lights in a room by room name.

    Args:
        room_name: The room name (from list_rooms). Case-insensitive.
        on: Turn on (true) or off (false).
        brightness: 0-100 percentage.
        color: Color name or hex (same as set_light).
        color_temp: Temperature preset (same as set_light).
    """
    group_id = _find_group_by_name(room_name)
    if not group_id:
        return f"Room '{room_name}' not found. Use list_rooms to see available rooms."

    state = _build_state(on, brightness, color, color_temp)
    if not state:
        return "No changes specified."

    result = _request(f"/groups/{group_id}/action", method="PUT", body=state)
    return _format_result(result)


@mcp.tool()
def activate_scene(scene_name: str) -> str:
    """
    Activate a saved scene by name. Case-insensitive partial match.

    Args:
        scene_name: The scene name (from list_scenes).
    """
    scenes = _request("/scenes")
    if isinstance(scenes, dict) and "error" in scenes:
        return scenes["error"]

    scene_name_lower = scene_name.lower()
    for scene_id, scene in scenes.items():
        if scene_name_lower in scene["name"].lower():
            group_id = scene.get("group", "0")
            result = _request(f"/groups/{group_id}/action", method="PUT",
                              body={"scene": scene_id})
            return f"Activated scene '{scene['name']}'. {_format_result(result)}"

    return f"Scene '{scene_name}' not found. Use list_scenes to see available scenes."


@mcp.tool()
def set_all_lights(on: bool | None = None, brightness: int | None = None,
                   color: str | None = None, color_temp: str | None = None) -> str:
    """
    Control ALL lights at once.

    Args:
        on: Turn all on (true) or off (false).
        brightness: 0-100 percentage.
        color: Color name or hex.
        color_temp: Temperature preset.
    """
    state = _build_state(on, brightness, color, color_temp)
    if not state:
        return "No changes specified."

    # Group 0 is the special "all lights" group
    result = _request("/groups/0/action", method="PUT", body=state)
    return _format_result(result)


# ---- Hue Sync tools ----

def _sync_status() -> tuple[bool, bool]:
    """Check if Hue Sync app is running and if sync is active.
    Returns (app_running, sync_active)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", '''
tell application "System Events"
    if exists process "Hue Sync" then
        tell process "Hue Sync"
            tell window 1
                return "running," & (value of checkbox 6)
            end tell
        end tell
    else
        return "not_running"
    end if
end tell'''],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.strip()
        if output == "not_running":
            return False, False
        parts = output.split(",")
        return True, parts[1] == "1"
    except Exception:
        return False, False


def _click_sync_button() -> str:
    """Launch Hue Sync if needed, then click the Start/Stop sync button."""
    # Activate the app (launches if not running)
    subprocess.run(["osascript", "-e", 'tell application "Hue Sync" to activate'],
                   capture_output=True, timeout=5)
    # Wait for app to be ready
    import time
    time.sleep(3)
    # Get button coordinates dynamically
    result = subprocess.run(
        ["osascript", "-e", '''
tell application "System Events"
    tell process "Hue Sync"
        set frontmost to true
        tell window 1
            set btnPos to position of checkbox 6
            set btnSize to size of checkbox 6
            set cx to (item 1 of btnPos) + (item 1 of btnSize) / 2
            set cy to (item 2 of btnPos) + (item 2 of btnSize) / 2
        end tell
    end tell
end tell
return (cx as integer as text) & "," & (cy as integer as text)'''],
        capture_output=True, text=True, timeout=10
    )
    coords = result.stdout.strip()
    if not coords:
        return f"Failed to get button coordinates: {result.stderr.strip()}"
    # Click with cliclick
    time.sleep(0.5)
    subprocess.run(["cliclick", f"c:{coords}"], capture_output=True, timeout=5)
    return coords


@mcp.tool()
def start_sync() -> str:
    """
    Start Hue Sync — syncs lights to screen/audio content.
    Launches the Hue Sync app if it's not already running.
    """
    running, active = _sync_status()
    if active:
        return "Hue Sync is already running."
    _click_sync_button()
    return "Hue Sync started."


@mcp.tool()
def stop_sync() -> str:
    """
    Stop Hue Sync.
    """
    running, active = _sync_status()
    if not running:
        return "Hue Sync app is not running."
    if not active:
        return "Hue Sync is not currently syncing."
    _click_sync_button()
    return "Hue Sync stopped."


# ---- Helpers ----

# Named color -> Hue xy coordinates (CIE 1931 color space)
_COLORS = {
    "red":        (0.675, 0.322),
    "green":      (0.409, 0.518),
    "blue":       (0.167, 0.04),
    "purple":     (0.3, 0.15),
    "orange":     (0.6, 0.38),
    "pink":       (0.45, 0.22),
    "yellow":     (0.5, 0.44),
    "white":      (0.3227, 0.329),
    "cyan":       (0.17, 0.34),
    "magenta":    (0.385, 0.155),
}

# Color temperature presets -> mirek values (153=cold to 500=warm)
_COLOR_TEMPS = {
    "candlelight": 500,
    "warm":        400,
    "sunset":      370,
    "daylight":    250,
    "cool":        200,
}


def _build_state(on: bool | None, brightness: int | None,
                 color: str | None, color_temp: str | None) -> dict:
    """Build a Hue state dict from the given parameters."""
    state = {}

    if on is not None:
        state["on"] = on

    if brightness is not None:
        state["bri"] = max(1, min(254, int(brightness / 100 * 254)))
        if "on" not in state:
            state["on"] = True  # turn on if setting brightness

    if color is not None:
        color_lower = color.lower().strip()
        if color_lower in _COLORS:
            state["xy"] = list(_COLORS[color_lower])
            if "on" not in state:
                state["on"] = True
        elif color_lower.startswith("#") and len(color_lower) == 7:
            xy = _hex_to_xy(color_lower)
            if xy:
                state["xy"] = list(xy)
                if "on" not in state:
                    state["on"] = True

    if color_temp is not None:
        temp_lower = color_temp.lower().strip()
        if temp_lower in _COLOR_TEMPS:
            state["ct"] = _COLOR_TEMPS[temp_lower]
            if "on" not in state:
                state["on"] = True

    return state


def _hex_to_xy(hex_color: str) -> tuple[float, float] | None:
    """Convert hex color to CIE xy coordinates for Hue."""
    try:
        r = int(hex_color[1:3], 16) / 255
        g = int(hex_color[3:5], 16) / 255
        b = int(hex_color[5:7], 16) / 255

        # Gamma correction
        r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
        g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
        b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92

        # Wide RGB to XYZ
        X = r * 0.664511 + g * 0.154324 + b * 0.162028
        Y = r * 0.283881 + g * 0.668433 + b * 0.047685
        Z = r * 0.000088 + g * 0.072310 + b * 0.986039

        total = X + Y + Z
        if total == 0:
            return (0.3227, 0.329)
        return (X / total, Y / total)
    except (ValueError, IndexError):
        return None


def _find_group_by_name(name: str) -> str | None:
    """Find a group ID by name (case-insensitive)."""
    groups = _request("/groups")
    if isinstance(groups, dict) and "error" in groups:
        return None

    name_lower = name.lower()
    for group_id, group in groups.items():
        if group["name"].lower() == name_lower:
            return group_id
    return None


def _format_result(result) -> str:
    """Format the Hue API response into a readable string."""
    if isinstance(result, dict) and "error" in result:
        return result["error"]

    if isinstance(result, list):
        successes = [r.get("success", {}) for r in result if "success" in r]
        errors = [r.get("error", {}).get("description", "") for r in result if "error" in r]
        parts = []
        if successes:
            parts.append("Done.")
        if errors:
            parts.append("Errors: " + "; ".join(errors))
        return " ".join(parts) if parts else "Done."

    return "Done."


if __name__ == "__main__":
    mcp.run(transport="stdio")
