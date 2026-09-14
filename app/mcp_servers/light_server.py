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
import fcntl
import subprocess
import asyncio
import ssl
import time
from datetime import datetime
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
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

HUE_IP_FILE = Path(__file__).parent.parent / ".hue_bridge_ip"


class HueBackend(LightBackend):
    prefix = "hue"

    # Philips cloud discovery — returns bridges on the caller's LAN. Used to
    # self-heal when the bridge's DHCP address changes (e.g. after a power cycle).
    DISCOVERY_URL = "https://discovery.meethue.com/"
    DEFAULT_BRIDGE_IP = "192.168.1.66"

    def __init__(self):
        self.api_key = get_secret("hue-api-key")
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE
        # Prefer the last-known-good IP, falling back to the default.
        self._set_bridge_ip(self._load_cached_ip() or self.DEFAULT_BRIDGE_IP, persist=False)

    def _set_bridge_ip(self, ip: str, persist: bool = True):
        self.bridge_ip = ip
        self.base_url = f"https://{ip}/api/{self.api_key}"
        if persist:
            try:
                HUE_IP_FILE.write_text(ip)
            except Exception:
                pass

    def _load_cached_ip(self) -> str | None:
        try:
            if HUE_IP_FILE.exists():
                return HUE_IP_FILE.read_text().strip() or None
        except Exception:
            pass
        return None

    def _discover_bridge(self) -> str | None:
        """Find the bridge's current IP via Philips cloud discovery."""
        try:
            with urllib.request.urlopen(self.DISCOVERY_URL, timeout=8) as resp:
                bridges = json.loads(resp.read())
            if bridges:
                return bridges[0].get("internalipaddress")
        except Exception:
            pass
        return None

    def _raw_request(self, path: str, method: str, body: dict | None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=10) as resp:
            return json.loads(resp.read())

    def _request(self, path: str, method: str = "GET", body: dict | None = None) -> dict | list:
        try:
            return self._raw_request(path, method, body)
        except urllib.error.URLError as e:
            # Bridge unreachable — its DHCP IP may have changed. Re-discover once.
            ip = self._discover_bridge()
            if ip and ip != self.bridge_ip:
                print(f"[HueBackend] Bridge moved to {ip}; updating.", file=sys.stderr)
                self._set_bridge_ip(ip)
                try:
                    return self._raw_request(path, method, body)
                except Exception as e2:
                    return {"error": f"Hue bridge unreachable after re-discovery ({ip}): {e2}"}
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
CYNC_LOCK_FILE = CYNC_TOKEN_FILE.with_name(".cync_tokens.lock")


@asynccontextmanager
async def _cync_file_lock():
    """
    Cross-process advisory lock around the Cync token file.

    Multiple services (dashboard, scheduler, telegram) each run their own
    light_server and share one .cync_tokens.json.  Cync uses single-use
    *rotating* refresh tokens, so two processes refreshing at once would
    invalidate each other's token.  This lock serializes the
    reload -> refresh -> persist critical section across processes.

    Acquired non-blockingly with async backoff so the event loop stays
    responsive while a sibling holds the lock.  Yields True if acquired,
    False on timeout (caller still proceeds best-effort).
    """
    fd = open(CYNC_LOCK_FILE, "w")
    acquired = False
    try:
        for _ in range(150):  # up to ~30s of contention
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                await asyncio.sleep(0.2)
        yield acquired
    finally:
        try:
            if acquired:
                fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        fd.close()

class CyncBackend(LightBackend):
    prefix = "cync"

    # Refresh the access token when it's within this many seconds of expiry.
    # Wider than pycync's internal 3600s window so OUR locked path always wins
    # the race against pycync's uncoordinated in-memory refresh.
    REFRESH_MARGIN = 7200

    # How long a state read waits for the mesh to answer a state query before
    # serving whatever pycync has cached.
    STATE_QUERY_TIMEOUT = float(os.environ.get("CYNC_STATE_TIMEOUT", "2.5"))

    def __init__(self):
        self._cync = None
        self._session = None
        self._auth = None
        # Serializes connect/refresh: the toolbus multiplexes every service onto
        # this one backend, and two concurrent _ensure_connected calls would
        # each open a Cync session — the cloud allows one per account, so the
        # pair evicts each other in an endless reconnect fight.
        self._conn_lock = asyncio.Lock()
        # Set by pycync's update callback whenever a state-query response (or
        # any device push) arrives; _refresh_state waits on it.
        self._state_fresh = asyncio.Event()
        # Set to a reason string when the last state read couldn't be trusted.
        self._state_stale: str | None = None

    def _load_tokens(self):
        if not CYNC_TOKEN_FILE.exists():
            return None
        return json.loads(CYNC_TOKEN_FILE.read_text())

    def _apply_tokens(self, auth, tokens):
        """Adopt the given tokens, mutating the existing User IN PLACE.

        pycync's TcpManager/CommandClient hold a reference to the User object
        they were created with — replacing auth._user with a new User leaves
        their reconnects logging in with the stale token. In-place mutation is
        what pycync's own refresh does (User.set_new_access_token), and it's
        what lets one TCP session live for the whole process lifetime.
        """
        user = getattr(auth, "_user", None)
        if user is None:
            from pycync.user import User
            auth._user = User(
                tokens["access_token"],
                tokens["refresh_token"],
                tokens.get("authorize", ""),
                tokens.get("user_id", 0),
                expires_at=tokens["expires_at"],
            )
        else:
            user._access_token = tokens["access_token"]
            user._refresh_token = tokens["refresh_token"]
            user._expires_at = tokens["expires_at"]

    def _write_tokens_atomic(self, auth):
        """Persist (possibly rotated) tokens atomically so siblings see them."""
        user = auth._user
        data = json.dumps({
            "access_token": user.access_token,
            "refresh_token": user.refresh_token,
            "expires_at": user.expires_at,
            "user_id": getattr(user, "user_id", ""),
            "authorize": getattr(user, "authorize", getattr(user, "_authorize", "")),
        })
        tmp = CYNC_TOKEN_FILE.with_name(CYNC_TOKEN_FILE.name + ".tmp")
        tmp.write_text(data)
        os.replace(tmp, CYNC_TOKEN_FILE)

    async def _sync_and_refresh(self, auth):
        """
        Under the cross-process lock: adopt the freshest token on disk (a sibling
        may have just rotated it), and if it's near expiry refresh exactly once,
        then persist the new single-use refresh token before releasing the lock.
        """
        async with _cync_file_lock():
            tokens = self._load_tokens()
            if tokens is None:
                # First-time login needs 2FA — run cync_setup.py first
                raise RuntimeError(
                    "Cync not authenticated. Run: python mcp_servers/cync_setup.py"
                )
            self._apply_tokens(auth, tokens)
            if auth._user.expires_at - time.time() < self.REFRESH_MARGIN:
                try:
                    await auth.async_refresh_user_token()
                except Exception as e:
                    # Cync refresh tokens are single-use and themselves expire.
                    # Once that happens no stored credential can recover the
                    # session — a fresh login needs the emailed 2FA code — so
                    # say that instead of surfacing a bare "Refresh token failed".
                    expired = datetime.fromtimestamp(auth._user.expires_at)
                    raise RuntimeError(
                        f"Cync session expired on {expired:%Y-%m-%d} and could not be "
                        f"refreshed ({e}). Re-authenticate with 2FA: "
                        f"./venv/bin/python app/mcp_servers/cync_setup.py"
                    ) from e
                self._write_tokens_atomic(auth)

    async def _ensure_connected(self):
        """Lazy-connect to the Cync cloud — ONE session for the process's life.

        The session is never rebuilt: token refresh mutates the live User in
        place (see _apply_tokens), so pycync's own reconnect logic keeps the
        same session working across drops and refreshes. The old rebuild-on-
        refresh / reconnect-on-timeout approach abandoned live sessions whose
        auto-reconnect loops can't be stopped (pycync shut_down doesn't cancel
        a pending reconnect task) — each orphan then fought the new session
        for the account's single allowed cloud connection, which is exactly
        the flakiness this replaces.
        """
        async with self._conn_lock:
            if self._cync is not None:
                if self._auth._user.expires_at - time.time() < self.REFRESH_MARGIN:
                    try:
                        await self._sync_and_refresh(self._auth)
                    except Exception as e:
                        # The session keeps working on the old token until real
                        # expiry — keep serving and retry on the next command.
                        print(f"[CyncBackend] Token refresh failed (will retry): {e}",
                              file=sys.stderr)
                return

            try:
                import aiohttp
                from pycync import Auth, Cync

                email = get_secret("cync-email")
                password = get_secret("cync-password")

                if self._session is None:
                    self._session = aiohttp.ClientSession()
                auth = Auth(self._session, username=email, password=password)

                await self._sync_and_refresh(auth)
                cync = await Cync.create(auth)
                # Any device push / state-query response marks state fresh.
                cync.set_update_callback(lambda _data: self._state_fresh.set())
                self._auth = auth
                self._cync = cync
            except ImportError:
                raise RuntimeError("pycync not installed: pip install pycync")
            except Exception as e:
                print(f"[CyncBackend] Connection failed: {e}", file=sys.stderr)
                # Surface the failure instead of silently returning zero lights.
                raise RuntimeError(f"Cync connection failed: {e}") from e

    async def _refresh_state(self):
        """Query the mesh for current device state and wait briefly for the
        answer. Without this, reads serve whatever attributes the last push
        packets happened to leave behind — the 'status is always wrong' bug."""
        self._state_fresh.clear()
        try:
            # pycync's _fetch_hub_device waits forever for the initial device
            # probe when no bulb is online, so the timeout must wrap the whole
            # update — NoHubConnectedError alone can't be relied on to fire.
            await asyncio.wait_for(
                self._cync._command_client.update_mesh_devices(),
                timeout=self.STATE_QUERY_TIMEOUT,
            )
        except Exception as e:
            # Silently serving cached state here is how "OFF, 0%, UNREACHABLE"
            # ends up looking like a fact instead of "we never heard back".
            detail = str(e).strip()
            self._state_stale = (
                f"mesh did not answer in {self.STATE_QUERY_TIMEOUT:g}s"
                if isinstance(e, (asyncio.TimeoutError, TimeoutError))
                else f"{type(e).__name__}: {detail}" if detail else type(e).__name__
            )
            print(f"[CyncBackend] state query failed ({self._state_stale}) — "
                  f"reporting cached/unknown state", file=sys.stderr)
            return
        try:
            await asyncio.wait_for(self._state_fresh.wait(), timeout=self.STATE_QUERY_TIMEOUT)
            self._state_stale = None
        except (asyncio.TimeoutError, TimeoutError):
            self._state_stale = f"no answer within {self.STATE_QUERY_TIMEOUT}s"
            print(f"[CyncBackend] mesh did not answer within {self.STATE_QUERY_TIMEOUT}s — "
                  f"reporting cached/unknown state", file=sys.stderr)

    async def list_lights(self) -> list[dict]:
        await self._ensure_connected()
        if not self._cync:
            return []
        await self._refresh_state()
        devices = self._cync.get_devices()
        result = []
        for dev in devices:
            entry = {
                "id": str(dev.mesh_reference_id),
                "name": dev.name,
                "on": getattr(dev, "is_on", False),
                "brightness_pct": getattr(dev, "brightness", 0),
                "reachable": getattr(dev, "is_online", True),
                # False when the mesh never answered: the on/brightness values
                # below are then pycync's defaults, not readings.
                "state_known": self._state_stale is None,
                "state_note": self._state_stale,
            }
            result.append(entry)
        return result

    async def list_rooms(self) -> list[dict]:
        await self._ensure_connected()
        if not self._cync:
            return []
        await self._refresh_state()
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
                    # Do NOT tear down / rebuild the session here — pycync
                    # reconnects on its own, and abandoning it spawns a rival
                    # session that fights this one for the account's single slot.
                    return "Error: Cync command timed out — try again in a moment."
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
#  Cync Proxy Backend (non-owner processes)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Loopback base URL of the dashboard's REST light API. The dashboard is the sole
# owner of the Cync cloud connection (flagged CYNC_OWNER=1); everyone else routes
# Cync commands here instead of opening a competing connection.
CYNC_PROXY_URL = os.environ.get("CYNC_PROXY_URL", "http://127.0.0.1:5001").rstrip("/")


class CyncProxyBackend(LightBackend):
    """
    Cync backend for non-owner processes (telegram, scheduler, CLI).

    Cync's cloud allows only ONE live TCP session per account — a second
    concurrent connection gets evicted, which used to trigger an endless
    reconnect storm between the dashboard's and telegram's light servers.
    So only the dashboard (CYNC_OWNER=1) holds a real pycync connection; this
    proxy forwards each operation to the dashboard's REST API over loopback,
    where the owner's real CyncBackend executes it.

    Only the 'cync:'-prefixed subset of the merged REST responses is used, so
    Hue (which each process still controls locally over the LAN) is untouched.
    """
    prefix = "cync"

    def __init__(self):
        self.base = CYNC_PROXY_URL
        self.api_key = get_secret("watch-api-key")
        # cync room id -> name, cached from the last list_rooms() so set_room()
        # (which receives an id) can address the owner's name-based endpoint.
        self._room_names: dict[str, str] = {}

    def _request(self, path: str, method: str = "GET", body: dict | None = None):
        url = f"{self.base}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read())

    async def _arequest(self, path: str, method: str = "GET", body: dict | None = None):
        # urllib is blocking; keep the event loop responsive.
        return await asyncio.to_thread(self._request, path, method, body)

    @staticmethod
    def _body(on, brightness, color, color_temp) -> dict:
        body = {}
        if on is not None:
            body["on"] = on
        if brightness is not None:
            body["brightness"] = brightness
        if color is not None:
            body["color"] = color
        if color_temp is not None:
            body["color_temp"] = color_temp
        return body

    async def list_lights(self) -> list[dict]:
        try:
            data = await self._arequest("/api/lights")
        except Exception as e:
            raise RuntimeError(f"Cync proxy unreachable (is the dashboard running?): {e}") from e
        result = []
        for l in data.get("lights", []):
            lid = l.get("id", "")
            if not lid.startswith("cync:"):
                continue
            result.append({
                "id": lid.split(":", 1)[1],
                "name": l.get("name", ""),
                "on": l.get("on", False),
                "brightness_pct": l.get("brightness", 0),
                "reachable": l.get("reachable", True),
                "state_known": l.get("state_known", True),
                "state_note": l.get("state_note"),
            })
        return result

    async def list_rooms(self) -> list[dict]:
        try:
            data = await self._arequest("/api/lights/rooms")
        except Exception as e:
            raise RuntimeError(f"Cync proxy unreachable (is the dashboard running?): {e}") from e
        result = []
        for r in data.get("rooms", []):
            rid = r.get("id", "")
            if not rid.startswith("cync:"):
                continue
            raw = rid.split(":", 1)[1]
            name = r.get("name", "")
            self._room_names[raw] = name
            result.append({
                "id": raw,
                "name": name,
                "type": r.get("type", "Room"),
                "on": r.get("on", False),
                "brightness_pct": r.get("brightness", 0),
                "light_count": r.get("light_count", 0),
            })
        return result

    async def set_light(self, light_id, on=None, brightness=None, color=None, color_temp=None):
        body = self._body(on, brightness, color, color_temp)
        if not body:
            return "No changes specified."
        try:
            data = await self._arequest(f"/api/lights/cync:{light_id}", method="PUT", body=body)
            return data.get("result", "Done.")
        except Exception as e:
            return f"Error: Cync proxy request failed: {e}"

    async def set_room(self, room_id, on=None, brightness=None, color=None, color_temp=None):
        body = self._body(on, brightness, color, color_temp)
        if not body:
            return "No changes specified."
        # The owner's REST endpoint addresses rooms by name; translate our id.
        name = self._room_names.get(room_id)
        if name is None:
            await self.list_rooms()
            name = self._room_names.get(room_id)
        if name is None:
            return "Cync room not found."
        from urllib.parse import quote
        try:
            data = await self._arequest(f"/api/lights/room/{quote(name)}", method="PUT", body=body)
            return data.get("result", "Done.")
        except Exception as e:
            return f"Error: Cync proxy request failed: {e}"

    async def set_all(self, on=None, brightness=None, color=None, color_temp=None):
        # Cync-only: fan out over our own lights rather than the dashboard's
        # merged /all endpoint, which would also drive Hue (handled locally).
        try:
            lights = await self.list_lights()
        except Exception as e:
            return f"Error: {e}"
        errors = []
        for l in lights:
            r = await self.set_light(l["id"], on=on, brightness=brightness,
                                     color=color, color_temp=color_temp)
            if r.startswith("Error"):
                errors.append(f"{l['name']}: {r}")
        if errors:
            return "Done with errors: " + "; ".join(errors)
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

# Cync ownership: exactly one process (the dashboard, launched with CYNC_OWNER=1)
# holds the real Cync cloud connection. Every other process proxies Cync
# commands to it over the dashboard's REST API, so only one TCP session to the
# Cync cloud ever exists. See CyncProxyBackend / main.py.
if os.environ.get("CYNC_OWNER") == "1":
    try:
        get_secret("cync-email")
        get_secret("cync-password")
        backends.append(CyncBackend())
    except RuntimeError:
        print("[light_server] Cync credentials not found in keychain — Cync backend disabled.", file=sys.stderr)
else:
    try:
        get_secret("watch-api-key")  # bearer token for the dashboard REST API
        backends.append(CyncProxyBackend())
    except RuntimeError:
        print("[light_server] watch-api-key not found — Cync proxy disabled.", file=sys.stderr)


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
                # An unconfirmed read must not be printed as a reading: pycync
                # defaults look exactly like "off at zero brightness", which
                # reads as fact and is how a dead mesh looked like real state.
                if not l.get("state_known", True):
                    note = l.get("state_note") or "no answer from the mesh"
                    lines.append(
                        f"[{backend.prefix}:{l['id']}] {l['name']} — state unknown "
                        f"({note}); the device is not reachable right now"
                    )
                    continue
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
