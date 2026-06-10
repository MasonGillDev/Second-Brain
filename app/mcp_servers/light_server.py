"""
Unified Light MCP Server.

Controls smart lights from multiple ecosystems (Hue, Cync) through a
single interface.  The agent sees one set of tools regardless of which
backend owns each light.

Light IDs are prefixed:  hue:<id>  /  cync:<id>
Room names are searched across all backends.
"""

import sys
import os
import json
import subprocess
import asyncio
import ssl
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from keychain import get_secret

mcp = FastMCP("lights")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Shared color maps
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NAMED_COLORS_RGB = {
    "red":      (255, 0, 0),
    "green":    (0, 255, 0),
    "blue":     (0, 0, 255),
    "purple":   (128, 0, 255),
    "orange":   (255, 165, 0),
    "pink":     (255, 105, 180),
    "yellow":   (255, 255, 0),
    "white":    (255, 255, 255),
    "cyan":     (0, 255, 255),
    "magenta":  (255, 0, 255),
}

# Hue xy coordinates (CIE 1931)
NAMED_COLORS_XY = {
    "red":      (0.675, 0.322),
    "green":    (0.409, 0.518),
    "blue":     (0.167, 0.04),
    "purple":   (0.3, 0.15),
    "orange":   (0.6, 0.38),
    "pink":     (0.45, 0.22),
    "yellow":   (0.5, 0.44),
    "white":    (0.3227, 0.329),
    "cyan":     (0.17, 0.34),
    "magenta":  (0.385, 0.155),
}

COLOR_TEMPS = {
    "candlelight": {"hue_mirek": 500, "cync_pct": 0},
    "warm":        {"hue_mirek": 400, "cync_pct": 20},
    "sunset":      {"hue_mirek": 370, "cync_pct": 30},
    "daylight":    {"hue_mirek": 250, "cync_pct": 65},
    "cool":        {"hue_mirek": 200, "cync_pct": 100},
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int] | None:
    try:
        return (int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16))
    except (ValueError, IndexError):
        return None


def _rgb_to_xy(r: int, g: int, b: int) -> tuple[float, float]:
    """Convert RGB to CIE xy for Hue."""
    rf, gf, bf = r / 255, g / 255, b / 255
    rf = ((rf + 0.055) / 1.055) ** 2.4 if rf > 0.04045 else rf / 12.92
    gf = ((gf + 0.055) / 1.055) ** 2.4 if gf > 0.04045 else gf / 12.92
    bf = ((bf + 0.055) / 1.055) ** 2.4 if bf > 0.04045 else bf / 12.92
    X = rf * 0.664511 + gf * 0.154324 + bf * 0.162028
    Y = rf * 0.283881 + gf * 0.668433 + bf * 0.047685
    Z = rf * 0.000088 + gf * 0.072310 + bf * 0.986039
    total = X + Y + Z
    if total == 0:
        return (0.3227, 0.329)
    return (X / total, Y / total)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Backend ABC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LightBackend(ABC):
    prefix: str  # "hue" or "cync"

    @abstractmethod
    async def list_lights(self) -> list[dict]:
        """Return list of {id, name, on, brightness_pct, reachable}."""

    @abstractmethod
    async def list_rooms(self) -> list[dict]:
        """Return list of {id, name, on, brightness_pct, light_count}."""

    @abstractmethod
    async def set_light(self, light_id: str, on: bool | None = None,
                        brightness: int | None = None, color: str | None = None,
                        color_temp: str | None = None) -> str:
        ...

    @abstractmethod
    async def set_room(self, room_id: str, on: bool | None = None,
                       brightness: int | None = None, color: str | None = None,
                       color_temp: str | None = None) -> str:
        ...

    @abstractmethod
    async def set_all(self, on: bool | None = None, brightness: int | None = None,
                      color: str | None = None, color_temp: str | None = None) -> str:
        ...

    async def list_scenes(self) -> list[dict]:
        return []

    async def activate_scene(self, scene_name: str) -> str:
        return "Scenes not supported on this backend."

    def find_room_by_name(self, rooms: list[dict], name: str) -> dict | None:
        name_lower = name.lower()
        for room in rooms:
            if room["name"].lower() == name_lower:
                return room
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Hue Backend
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class HueBackend(LightBackend):
    prefix = "hue"

    def __init__(self):
        self.bridge_ip = "192.168.1.65"
        self.api_key = get_secret("hue-api-key")
        self.base_url = f"https://{self.bridge_ip}/api/{self.api_key}"
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def _request(self, path: str, method: str = "GET", body: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=10) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            return {"error": f"Hue bridge unreachable: {e}"}
        except Exception as e:
            return {"error": str(e)}

    def _build_state(self, on, brightness, color, color_temp):
        state = {}
        if on is not None:
            state["on"] = on
        if brightness is not None:
            state["bri"] = max(1, min(254, int(brightness / 100 * 254)))
            if "on" not in state:
                state["on"] = True
        if color is not None:
            color_lower = color.lower().strip()
            xy = None
            if color_lower in NAMED_COLORS_XY:
                xy = NAMED_COLORS_XY[color_lower]
            elif color_lower.startswith("#") and len(color_lower) == 7:
                rgb = _hex_to_rgb(color_lower)
                if rgb:
                    xy = _rgb_to_xy(*rgb)
            if xy:
                state["xy"] = list(xy)
                if "on" not in state:
                    state["on"] = True
        if color_temp is not None:
            temp_lower = color_temp.lower().strip()
            if temp_lower in COLOR_TEMPS:
                state["ct"] = COLOR_TEMPS[temp_lower]["hue_mirek"]
                if "on" not in state:
                    state["on"] = True
        return state

    def _format_result(self, result) -> str:
        if isinstance(result, dict) and "error" in result:
            return result["error"]
        if isinstance(result, list):
            errors = [r.get("error", {}).get("description", "") for r in result if "error" in r]
            if errors:
                return "Done. Errors: " + "; ".join(errors)
        return "Done."

    async def list_lights(self) -> list[dict]:
        lights = self._request("/lights")
        if isinstance(lights, dict) and "error" in lights:
            return []
        result = []
        for lid, light in sorted(lights.items(), key=lambda x: int(x[0])):
            state = light["state"]
            result.append({
                "id": lid,
                "name": light["name"],
                "on": state["on"],
                "brightness_pct": int(state["bri"] / 254 * 100),
                "reachable": state["reachable"],
            })
        return result

    async def list_rooms(self) -> list[dict]:
        groups = self._request("/groups")
        if isinstance(groups, dict) and "error" in groups:
            return []
        result = []
        for gid, group in sorted(groups.items(), key=lambda x: int(x[0])):
            action = group.get("action", {})
            result.append({
                "id": gid,
                "name": group["name"],
                "type": group.get("type", "Group"),
                "on": action.get("on", False),
                "brightness_pct": int(action.get("bri", 0) / 254 * 100),
                "light_count": len(group.get("lights", [])),
            })
        return result

    async def set_light(self, light_id, on=None, brightness=None, color=None, color_temp=None):
        state = self._build_state(on, brightness, color, color_temp)
        if not state:
            return "No changes specified."
        return self._format_result(self._request(f"/lights/{light_id}/state", method="PUT", body=state))

    async def set_room(self, room_id, on=None, brightness=None, color=None, color_temp=None):
        state = self._build_state(on, brightness, color, color_temp)
        if not state:
            return "No changes specified."
        return self._format_result(self._request(f"/groups/{room_id}/action", method="PUT", body=state))

    async def set_all(self, on=None, brightness=None, color=None, color_temp=None):
        state = self._build_state(on, brightness, color, color_temp)
        if not state:
            return "No changes specified."
        return self._format_result(self._request("/groups/0/action", method="PUT", body=state))

    async def list_scenes(self) -> list[dict]:
        scenes = self._request("/scenes")
        if isinstance(scenes, dict) and "error" in scenes:
            return []
        result = []
        for sid, scene in scenes.items():
            result.append({
                "id": sid,
                "name": scene["name"],
                "group": scene.get("group", "?"),
            })
        return result

    async def activate_scene(self, scene_name: str) -> str:
        scenes = self._request("/scenes")
        if isinstance(scenes, dict) and "error" in scenes:
            return scenes["error"]
        name_lower = scene_name.lower()
        for scene_id, scene in scenes.items():
            if name_lower in scene["name"].lower():
                group_id = scene.get("group", "0")
                result = self._request(f"/groups/{group_id}/action", method="PUT",
                                       body={"scene": scene_id})
                return f"Activated scene '{scene['name']}'. {self._format_result(result)}"
        return f"Scene '{scene_name}' not found."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Cync Backend
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CYNC_TOKEN_FILE = Path(__file__).parent.parent / ".cync_tokens.json"

class CyncBackend(LightBackend):
    prefix = "cync"

    def __init__(self):
        self._cync = None
        self._session = None
        self._devices = []
        self._homes = []
        self._connected = False

    async def _ensure_connected(self):
        """Lazy-connect to the Cync cloud on first use."""
        if self._connected:
            return
        try:
            import aiohttp
            from pycync import Auth, Cync
            from pycync.user import User

            email = get_secret("cync-email")
            password = get_secret("cync-password")

            if self._session is None:
                self._session = aiohttp.ClientSession()
            auth = Auth(self._session, username=email, password=password)

            # Try to restore cached tokens
            if CYNC_TOKEN_FILE.exists():
                tokens = json.loads(CYNC_TOKEN_FILE.read_text())
                # Build a real User so token refresh (set_new_access_token) works.
                auth._user = User(
                    tokens["access_token"],
                    tokens["refresh_token"],
                    tokens.get("authorize", ""),
                    tokens.get("user_id", 0),
                    expires_at=tokens["expires_at"],
                )
                # Refresh if close to / past expiry
                if auth._user.expires_at - time.time() < 3600:
                    await auth.async_refresh_user_token()
            else:
                # First-time login needs 2FA — run cync_setup.py first
                raise RuntimeError(
                    "Cync not authenticated. Run: python mcp_servers/cync_setup.py"
                )

            self._cync = await Cync.create(auth)
            self._connected = True
            self._cache_tokens(auth)
        except ImportError:
            raise RuntimeError("pycync not installed: pip install pycync")
        except Exception as e:
            print(f"[CyncBackend] Connection failed: {e}", file=sys.stderr)
            self._connected = False
            # Surface the failure instead of silently returning zero lights.
            raise RuntimeError(f"Cync connection failed: {e}") from e

    def _cache_tokens(self, auth):
        """Save auth tokens for next startup."""
        try:
            user = auth._user
            CYNC_TOKEN_FILE.write_text(json.dumps({
                "access_token": user.access_token,
                "refresh_token": user.refresh_token,
                "expires_at": user.expires_at,
                "user_id": getattr(user, "user_id", ""),
                "authorize": getattr(user, "authorize", getattr(user, "_authorize", "")),
            }))
        except Exception:
            pass

    async def list_lights(self) -> list[dict]:
        await self._ensure_connected()
        if not self._cync:
            return []
        devices = self._cync.get_devices()
        result = []
        for dev in devices:
            entry = {
                "id": str(dev.mesh_reference_id),
                "name": dev.name,
                "on": getattr(dev, "is_on", False),
                "brightness_pct": getattr(dev, "brightness", 0),
                "reachable": getattr(dev, "is_online", True),
            }
            result.append(entry)
        return result

    async def list_rooms(self) -> list[dict]:
        await self._ensure_connected()
        if not self._cync:
            return []
        homes = self._cync.get_homes()
        result = []
        for home in homes:
            for room in getattr(home, "rooms", []):
                devices = getattr(room, "devices", [])
                any_on = any(getattr(d, "is_on", False) for d in devices)
                avg_bri = 0
                if devices:
                    avg_bri = sum(getattr(d, "brightness", 0) for d in devices) // len(devices)
                result.append({
                    "id": str(getattr(room, "id", room.name)),
                    "name": room.name,
                    "type": "Room",
                    "on": any_on,
                    "brightness_pct": avg_bri,
                    "light_count": len(devices),
                })
        return result

    def _resolve_color(self, color: str | None) -> tuple[int, int, int] | None:
        if color is None:
            return None
        color_lower = color.lower().strip()
        if color_lower in NAMED_COLORS_RGB:
            return NAMED_COLORS_RGB[color_lower]
        if color_lower.startswith("#") and len(color_lower) == 7:
            return _hex_to_rgb(color_lower)
        return None

    def _resolve_color_temp(self, color_temp: str | None) -> int | None:
        if color_temp is None:
            return None
        temp_lower = color_temp.lower().strip()
        if temp_lower in COLOR_TEMPS:
            return COLOR_TEMPS[temp_lower]["cync_pct"]
        return None

    async def _apply_to_device(self, dev, on, brightness, color, color_temp):
        """Apply state changes to a single CyncLight device."""
        rgb = self._resolve_color(color)
        ct = self._resolve_color_temp(color_temp)

        async def _send():
            # pycync turn_on/turn_off are broken (missing mesh_id), so always use set_combo
            if hasattr(dev, "set_combo"):
                _on = on if on is not None else True
                _bri = brightness if brightness is not None else (0 if not _on else (getattr(dev, "brightness", 100) or 100))
                await dev.set_combo(_on, _bri, color_temp=ct, rgb=rgb)
            else:
                if on is True:
                    await dev.turn_on()
                elif on is False:
                    await dev.turn_off()
                if brightness is not None:
                    await dev.set_brightness(brightness)
                if rgb is not None:
                    await dev.set_rgb(rgb)
                if ct is not None:
                    await dev.set_color_temp(ct)

        await asyncio.wait_for(_send(), timeout=8)

    async def set_light(self, light_id, on=None, brightness=None, color=None, color_temp=None):
        await self._ensure_connected()
        if not self._cync:
            return "Cync not connected."
        devices = self._cync.get_devices()
        for dev in devices:
            if str(dev.mesh_reference_id) == light_id:
                try:
                    # Turn on implicitly if setting brightness/color
                    if on is None and (brightness is not None or color is not None or color_temp is not None):
                        on = True
                    await self._apply_to_device(dev, on, brightness, color, color_temp)
                    return "Done."
                except TimeoutError:
                    self._connected = False
                    return "Error: Cync command timed out — will reconnect on next attempt."
                except Exception as e:
                    return f"Error: {e}"
        return f"Cync light '{light_id}' not found."

    async def set_room(self, room_id, on=None, brightness=None, color=None, color_temp=None):
        await self._ensure_connected()
        if not self._cync:
            return "Cync not connected."
        # Collect device IDs from the room, then use live device objects from get_devices()
        room_device_ids = set()
        homes = self._cync.get_homes()
        for home in homes:
            for room in getattr(home, "rooms", []):
                rid = str(getattr(room, "id", room.name))
                if rid == room_id:
                    for dev in getattr(room, "devices", []):
                        room_device_ids.add(str(dev.mesh_reference_id))
                    break
            if room_device_ids:
                break
        if not room_device_ids:
            return "Cync room not found."
        if on is None and (brightness is not None or color is not None or color_temp is not None):
            on = True
        live_devices = self._cync.get_devices()
        errors = []
        controlled = 0
        for dev in live_devices:
            if str(dev.mesh_reference_id) in room_device_ids:
                try:
                    await self._apply_to_device(dev, on, brightness, color, color_temp)
                    controlled += 1
                except TimeoutError:
                    self._connected = False
                    errors.append(f"{dev.name}: timed out")
                except Exception as e:
                    errors.append(f"{dev.name}: {e}")
        if errors:
            return f"Done ({controlled} ok). Errors: " + "; ".join(errors)
        return "Done."

    async def set_all(self, on=None, brightness=None, color=None, color_temp=None):
        await self._ensure_connected()
        if not self._cync:
            return "Cync not connected."
        if on is None and (brightness is not None or color is not None or color_temp is not None):
            on = True
        devices = self._cync.get_devices()
        for dev in devices:
            try:
                await self._apply_to_device(dev, on, brightness, color, color_temp)
            except Exception:
                pass
        return "Done."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Hue Sync (macOS app control — Hue-specific)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _sync_status() -> tuple[bool, bool]:
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
    subprocess.run(["osascript", "-e", 'tell application "Hue Sync" to activate'],
                   capture_output=True, timeout=5)
    time.sleep(3)
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
    time.sleep(0.5)
    subprocess.run(["cliclick", f"c:{coords}"], capture_output=True, timeout=5)
    return coords


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Backend registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

backends: list[LightBackend] = [HueBackend()]

# Only add Cync if credentials are available
try:
    get_secret("cync-email")
    get_secret("cync-password")
    backends.append(CyncBackend())
except RuntimeError:
    print("[light_server] Cync credentials not found in keychain — Cync backend disabled.", file=sys.stderr)


def _get_backend(prefixed_id: str) -> tuple[LightBackend, str] | tuple[None, None]:
    """Parse 'hue:3' or 'cync:42' into (backend, raw_id)."""
    if ":" in prefixed_id:
        prefix, raw_id = prefixed_id.split(":", 1)
        for b in backends:
            if b.prefix == prefix:
                return b, raw_id
    # Fallback: try without prefix (assume Hue for backwards compat)
    for b in backends:
        if b.prefix == "hue":
            return b, prefixed_id
    return None, None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MCP Tools
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def list_lights() -> str:
    """
    List all smart lights with their current state.
    Shows: ID (prefixed), name, on/off, brightness %, reachability.
    IDs are prefixed with the system (e.g. hue:1, cync:42).
    """
    lines = []
    for backend in backends:
        try:
            lights = await backend.list_lights()
            for l in lights:
                on = "ON" if l["on"] else "OFF"
                reachable = "reachable" if l["reachable"] else "UNREACHABLE"
                lines.append(
                    f"[{backend.prefix}:{l['id']}] {l['name']} — {on}, "
                    f"{l['brightness_pct']}% brightness ({reachable})"
                )
        except Exception as e:
            lines.append(f"[{backend.prefix}] Error: {e}")
    return "\n".join(lines) if lines else "No lights found."


@mcp.tool()
async def list_rooms() -> str:
    """
    List all rooms/groups across all light systems with their current state.
    """
    lines = []
    for backend in backends:
        try:
            rooms = await backend.list_rooms()
            for r in rooms:
                on = "ON" if r["on"] else "OFF"
                lines.append(
                    f"[{backend.prefix}:{r['id']}] {r['name']} "
                    f"({r.get('type', 'Room')}) — {on}, "
                    f"{r['brightness_pct']}%, {r['light_count']} lights"
                )
        except Exception as e:
            lines.append(f"[{backend.prefix}] Error: {e}")
    return "\n".join(lines) if lines else "No rooms found."


@mcp.tool()
async def list_scenes() -> str:
    """
    List all saved scenes. Scenes are preconfigured light states
    that can be activated to set mood/ambiance.
    """
    lines = []
    for backend in backends:
        try:
            scenes = await backend.list_scenes()
            for s in scenes:
                lines.append(f"[{backend.prefix}:{s['id']}] {s['name']} (group {s.get('group', '?')})")
        except Exception:
            pass
    return "\n".join(lines) if lines else "No scenes found."


@mcp.tool()
async def set_light(light_id: str, on: bool | None = None, brightness: int | None = None,
                    color: str | None = None, color_temp: str | None = None) -> str:
    """
    Control a specific light by its prefixed ID (e.g. "hue:3" or "cync:42").

    Args:
        light_id: The light ID from list_lights (e.g. "hue:3", "cync:42").
        on: Turn on (true) or off (false). Omit to keep current state.
        brightness: 0-100 percentage.
        color: Color name ("red", "blue", "green", "purple", "orange", "pink",
               "yellow", "white") or hex ("#FF0000").
        color_temp: Temperature preset: "warm", "cool", "daylight",
                    "candlelight", "sunset".
    """
    backend, raw_id = _get_backend(light_id)
    if not backend:
        return f"Unknown light system in '{light_id}'. Use list_lights to see available lights."
    return await backend.set_light(raw_id, on=on, brightness=brightness,
                                   color=color, color_temp=color_temp)


@mcp.tool()
async def set_room(room_name: str, on: bool | None = None, brightness: int | None = None,
                   color: str | None = None, color_temp: str | None = None) -> str:
    """
    Control all lights in a room by name. Searches across all light systems.

    Args:
        room_name: The room name (case-insensitive). Searched across all systems.
        on: Turn on (true) or off (false).
        brightness: 0-100 percentage.
        color: Color name or hex (same as set_light).
        color_temp: Temperature preset (same as set_light).
    """
    for backend in backends:
        try:
            rooms = await backend.list_rooms()
            match = backend.find_room_by_name(rooms, room_name)
            if match:
                return await backend.set_room(match["id"], on=on, brightness=brightness,
                                              color=color, color_temp=color_temp)
        except Exception as e:
            return f"Error: {e}"
    return f"Room '{room_name}' not found. Use list_rooms to see available rooms."


@mcp.tool()
async def activate_scene(scene_name: str) -> str:
    """
    Activate a saved scene by name. Case-insensitive partial match.

    Args:
        scene_name: The scene name (from list_scenes).
    """
    for backend in backends:
        try:
            result = await backend.activate_scene(scene_name)
            if "not found" not in result.lower() and "not supported" not in result.lower():
                return result
        except Exception:
            pass
    return f"Scene '{scene_name}' not found. Use list_scenes to see available scenes."


@mcp.tool()
async def set_all_lights(on: bool | None = None, brightness: int | None = None,
                         color: str | None = None, color_temp: str | None = None) -> str:
    """
    Control ALL lights across all systems at once.

    Args:
        on: Turn all on (true) or off (false).
        brightness: 0-100 percentage.
        color: Color name or hex.
        color_temp: Temperature preset.
    """
    results = []
    for backend in backends:
        try:
            r = await backend.set_all(on=on, brightness=brightness,
                                      color=color, color_temp=color_temp)
            results.append(f"{backend.prefix}: {r}")
        except Exception as e:
            results.append(f"{backend.prefix}: Error — {e}")
    return " | ".join(results)


@mcp.tool()
async def start_sync() -> str:
    """
    Start Hue Sync — syncs Hue lights to screen/audio content.
    Launches the Hue Sync app if it's not already running.
    """
    running, active = _sync_status()
    if active:
        return "Hue Sync is already running."
    _click_sync_button()
    return "Hue Sync started."


@mcp.tool()
async def stop_sync() -> str:
    """Stop Hue Sync."""
    running, active = _sync_status()
    if not running:
        return "Hue Sync app is not running."
    if not active:
        return "Hue Sync is not currently syncing."
    _click_sync_button()
    return "Hue Sync stopped."


if __name__ == "__main__":
    import logging
    logging.getLogger("mcp.server").setLevel(logging.WARNING)
    mcp.run(transport="stdio")
