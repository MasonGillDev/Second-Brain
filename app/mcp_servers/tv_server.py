"""
Samsung TV MCP Server.

Controls the Samsung TU7000 55" TV over the local network using the Tizen
WebSocket remote API (samsungtvws) — no cloud account required.

Power-on uses Wake-on-LAN (the TV must have "Power On with Mobile" enabled:
Settings > General > Network > Expert Settings). Everything else goes over
the token-authenticated WebSocket on port 8002; the first-ever connection
pops an "Allow" prompt on the TV that must be accepted once with the remote.

If the TV's DHCP address changes, the server re-discovers it via SSDP and
verifies the match by MAC address.
"""

import sys
import os
import re
import json
import time
import socket
import struct
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tv")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TV identity / files
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFAULT_TV_IP = "192.168.1.110"
TV_MAC = "10:2B:41:23:80:5A"          # wifiMac from the TV's REST info API
CLIENT_NAME = "SecondBrain"           # shown in the TV's device-manager list

TV_IP_FILE = Path(__file__).parent.parent / ".tv_ip"
TV_TOKEN_FILE = Path(__file__).parent.parent / ".tv_token.txt"

REST_TIMEOUT = 3
# Hard ceiling on any single TV websocket call. samsungtvws' own timeout covers
# connecting, not waiting for a reply the TV never sends: app_list() on this
# TU7000 firmware blocks forever. Because this MCP server is single-threaded,
# one such call wedges it permanently and every TV tool stops answering until
# the server restarts — which is exactly how "the TV tools stopped working".
WS_CALL_TIMEOUT = float(os.environ.get("TV_WS_TIMEOUT", "10"))

# App IDs verified installed on this TV via GET /api/v2/applications/<id>
# (the WebSocket app_list hangs on this firmware, so this map is primary).
KNOWN_APPS = {
    "netflix": "3201907018807",
    "youtube": "111299001912",
    "prime video": "3201910019365",
    "disney+": "3201901017640",
    "disney plus": "3201901017640",
    "hulu": "3201601007625",
    "spotify": "3201606009684",
    "apple tv": "3201807016597",
}

KEY_ALIASES = {
    "up": "KEY_UP", "down": "KEY_DOWN", "left": "KEY_LEFT", "right": "KEY_RIGHT",
    "enter": "KEY_ENTER", "ok": "KEY_ENTER", "select": "KEY_ENTER",
    "back": "KEY_RETURN", "return": "KEY_RETURN", "exit": "KEY_EXIT",
    "home": "KEY_HOME", "menu": "KEY_MENU", "source": "KEY_SOURCE",
    "play": "KEY_PLAY", "pause": "KEY_PAUSE", "stop": "KEY_STOP",
    "rewind": "KEY_REWIND", "fast_forward": "KEY_FF", "ff": "KEY_FF",
    "volume_up": "KEY_VOLUP", "volume_down": "KEY_VOLDOWN", "mute": "KEY_MUTE",
    "channel_up": "KEY_CHUP", "channel_down": "KEY_CHDOWN",
    "power": "KEY_POWER", "guide": "KEY_GUIDE", "info": "KEY_INFO",
    "tools": "KEY_TOOLS", "red": "KEY_RED", "green": "KEY_GREEN",
    "yellow": "KEY_YELLOW", "blue": "KEY_BLUE",
    **{str(n): f"KEY_{n}" for n in range(10)},
}

# This TV (TU7000) ignores the port-specific KEY_HDMI1/KEY_HDMI2 codes —
# verified 2026-07-01. KEY_HDMI works and cycles through HDMI ports on
# repeated presses, so hdmi1/hdmi2 map to 1/2 presses of it.
INPUT_KEYS = {
    "tv": ("KEY_TV", 1),
    "hdmi": ("KEY_HDMI", 1),
    "hdmi1": ("KEY_HDMI", 1),
    "hdmi2": ("KEY_HDMI", 2),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Discovery / REST info (no auth needed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_cached_ip() -> str:
    try:
        if TV_IP_FILE.exists():
            ip = TV_IP_FILE.read_text().strip()
            if ip:
                return ip
    except Exception:
        pass
    return DEFAULT_TV_IP


def _cache_ip(ip: str):
    try:
        TV_IP_FILE.write_text(ip)
    except Exception:
        pass


def _rest_info(ip: str) -> dict | None:
    """The TV's unauthenticated info endpoint. None if unreachable (deep sleep)."""
    try:
        with urllib.request.urlopen(f"http://{ip}:8001/api/v2/", timeout=REST_TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _rest_app(ip: str, app_id: str, method: str = "GET") -> dict:
    """The TV's HTTP app endpoint: GET = status, POST = launch, DELETE = close.
    Much faster than the WebSocket channel and needs no pairing.
    POST/DELETE answer with a junk body ("HTTP/"), so only GET is parsed."""
    req = urllib.request.Request(
        f"http://{ip}:8001/api/v2/applications/{app_id}",
        data=b"" if method == "POST" else None, method=method)
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = resp.read()
    if method != "GET":
        return {}
    return json.loads(raw or b"{}")


def _visible_app(ip: str) -> str | None:
    """Which known app is currently on screen, if any."""
    seen = set()
    for name, app_id in KNOWN_APPS.items():
        if app_id in seen:
            continue
        seen.add(app_id)
        try:
            if _rest_app(ip, app_id).get("visible"):
                return name
        except Exception:
            pass
    return None


def _ssdp_discover() -> str | None:
    """Find the TV's current IP via SSDP, verified by MAC."""
    msg = "\r\n".join([
        "M-SEARCH * HTTP/1.1", "HOST: 239.255.255.250:1900",
        'MAN: "ssdp:discover"', "MX: 2", "ST: ssdp:all", "", ""]).encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.settimeout(3)
    candidates = set()
    try:
        s.sendto(msg, ("239.255.255.250", 1900))
        while True:
            try:
                data, addr = s.recvfrom(65507)
            except socket.timeout:
                break
            if b"Samsung" in data:
                candidates.add(addr[0])
    except OSError:
        return None
    finally:
        s.close()
    for ip in candidates:
        info = _rest_info(ip)
        if info and info.get("device", {}).get("wifiMac", "").upper() == TV_MAC.upper():
            return ip
    return None


def _tv_ip(rediscover: bool = True) -> str:
    """Last-known-good IP, self-healing via SSDP when the TV moved."""
    ip = _load_cached_ip()
    if _rest_info(ip) is not None:
        return ip
    if rediscover:
        found = _ssdp_discover()
        if found and found != ip:
            _cache_ip(found)
            return found
    return ip


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  WebSocket remote (token-paired)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_remote = None
_remote_ip = None
_last_use = 0.0

# The TV silently kills idle WebSocket connections, and a write to a dead
# socket can vanish WITHOUT raising — so the first keypress after an idle
# period was getting eaten (reported "Sent" but nothing happened on screen).
# Any connection idle past this many seconds is rebuilt (~0.2s) before use.
IDLE_RECONNECT_SECONDS = 30


def _get_remote(ip: str):
    """Lazy, reused WebSocket client. First-ever pairing pops a prompt on the TV,
    so use a generous timeout until a token exists."""
    global _remote, _remote_ip
    if _remote is not None and _remote_ip == ip:
        return _remote
    from samsungtvws import SamsungTVWS
    have_token = TV_TOKEN_FILE.exists() and TV_TOKEN_FILE.read_text().strip()
    # key_press_delay=0: the library sleeps that long after EVERY send_key;
    # tv_send_keys manages inter-key pacing itself.
    _remote = SamsungTVWS(
        host=ip, port=8002, token_file=str(TV_TOKEN_FILE),
        name=CLIENT_NAME, timeout=8 if have_token else 45, key_press_delay=0,
    )
    _remote_ip = ip
    return _remote


def _drop_remote():
    global _remote, _remote_ip
    try:
        if _remote is not None:
            _remote.close()
    except Exception:
        pass
    _remote = None
    _remote_ip = None


def _deadline(fn, seconds: float = WS_CALL_TIMEOUT):
    """Run a blocking TV call with a hard ceiling, raising TimeoutError instead
    of hanging.

    The worker is a daemon thread: a call stuck in the socket can't be killed,
    but it must not hold the server. Abandoning it costs one idle thread; not
    abandoning it costs every TV tool.
    """
    box: dict = {}

    def _run():
        try:
            box["value"] = fn()
        except BaseException as e:      # noqa: BLE001 - re-raised on the caller's thread
            box["error"] = e

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        raise TimeoutError(f"TV did not answer within {seconds:g}s")
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _with_remote(fn):
    """Run fn(remote), reconnecting once on a stale-connection failure.

    Uses the cached IP directly (no REST probe on the hot path — that cost
    seconds per call); only on failure does it verify/rediscover the IP.
    """
    global _last_use
    if _remote is not None and time.time() - _last_use > IDLE_RECONNECT_SECONDS:
        _drop_remote()
    try:
        result = _deadline(lambda: fn(_get_remote(_load_cached_ip())))
    except Exception:
        _drop_remote()
        try:
            result = _deadline(lambda: fn(_get_remote(_tv_ip())))
        except Exception:
            # Never leave a half-dead connection cached: the next call must
            # start clean rather than inherit a socket nobody is reading.
            _drop_remote()
            raise
    _last_use = time.time()
    return result


def _send_key(key: str):
    _with_remote(lambda r: r.send_key(key))


def _send_text(text: str):
    """Type into the TV's focused input field via the IME channel.
    Only works where the SYSTEM keyboard appears (Smart Hub search, browser);
    apps that draw their own keyboard don't receive this."""
    import base64
    payload = {
        "method": "ms.remote.control",
        "params": {
            "Cmd": base64.b64encode(text.encode()).decode(),
            "DataOfCmd": "base64",
            "TypeOfRemote": "SendInputString",
        },
    }
    _with_remote(lambda r: r._ws_send(payload, key_press_delay=0))


def _send_text_end():
    """Commit the IME input (closes the on-screen keyboard on most firmware)."""
    payload = {"method": "ms.remote.control",
               "params": {"TypeOfRemote": "SendInputEnd"}}
    _with_remote(lambda r: r._ws_send(payload, key_press_delay=0))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Wake-on-LAN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _send_wol():
    mac_bytes = bytes(int(b, 16) for b in TV_MAC.split(":"))
    packet = b"\xff" * 6 + mac_bytes * 16
    for target in ("255.255.255.255", "192.168.1.255"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for _ in range(3):
                s.sendto(packet, (target, 9))
            s.close()
        except OSError:
            pass


def _wake(timeout: float = 25) -> bool:
    """Send WoL until the TV reports powered on. True on success."""
    ip = _load_cached_ip()
    deadline = time.time() + timeout
    while time.time() < deadline:
        _send_wol()
        time.sleep(2)
        info = _rest_info(ip)
        if info and info.get("device", {}).get("PowerState") == "on":
            return True
    return False


def _ensure_on() -> tuple[bool, str | None]:
    """Wake the TV if it's off. Returns (woke_it, error_message)."""
    ip = _tv_ip()
    info = _rest_info(ip)
    if info and info.get("device", {}).get("PowerState") == "on":
        return False, None
    if _wake():
        time.sleep(2)  # give the app framework a beat after boot
        return True, None
    return False, ("TV is off and didn't respond to wake-up (deep sleep?). "
                   "Try tv_power(on=true), possibly twice.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UPnP volume (absolute set/get — the remote keys only step)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _upnp_volume(ip: str, action: str, value: int | None = None) -> int | None:
    arg = f"<DesiredVolume>{value}</DesiredVolume>" if action == "SetVolume" else ""
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
        f'<u:{action} xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">'
        f'<InstanceID>0</InstanceID><Channel>Master</Channel>{arg}'
        f'</u:{action}></s:Body></s:Envelope>'
    ).encode()
    req = urllib.request.Request(
        f"http://{ip}:9197/upnp/control/RenderingControl1", data=body, method="POST")
    req.add_header("Content-Type", 'text/xml; charset="utf-8"')
    req.add_header("SOAPACTION",
                   f'"urn:schemas-upnp-org:service:RenderingControl:1#{action}"')
    with urllib.request.urlopen(req, timeout=5) as resp:
        text = resp.read().decode(errors="replace")
    m = re.search(r"<CurrentVolume>(\d+)</CurrentVolume>", text)
    return int(m.group(1)) if m else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MCP Tools
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def tv_status() -> str:
    """
    Get the TV's current state: power, volume, and which app is on screen
    (app detection covers the known streaming apps; live TV/HDMI show as none).
    """
    ip = _tv_ip()
    info = _rest_info(ip)
    if info is None:
        return ("TV is OFF (deep sleep — not responding on the network). "
                "Use tv_power(on=true) to wake it.")
    dev = info.get("device", {})
    power = dev.get("PowerState", "unknown")
    lines = [
        f"Power: {power}",
        f"Name: {dev.get('name', '?')}  Model: {dev.get('modelName', '?')}",
        f"IP: {ip}",
    ]
    if power == "on":
        try:
            vol = _upnp_volume(ip, "GetVolume")
            if vol is not None:
                lines.append(f"Volume: {vol}")
        except Exception:
            pass
        app = _visible_app(ip)
        lines.append(f"On screen: {app if app else 'no known app (live TV, HDMI input, or menu)'}")
    return "\n".join(lines)


@mcp.tool()
def tv_power(on: bool) -> str:
    """
    Turn the TV on or off.

    Power-on uses Wake-on-LAN and can take ~5-20 seconds while the TV boots.
    If the TV has been off a long time it may be in deep sleep and miss the
    first wake attempt — calling this again usually gets it.

    Args:
        on: true to turn on, false to turn off.
    """
    ip = _tv_ip()
    info = _rest_info(ip)
    powered_on = info is not None and info.get("device", {}).get("PowerState") == "on"

    if on:
        if powered_on:
            return "TV is already on."
        if _wake():
            return "TV is on."
        return ("TV didn't wake up (it may be in deep sleep). "
                "Try tv_power(on=true) once more; if it still fails, the TV "
                "may have lost its WiFi standby connection.")
    else:
        if info is None:
            return "TV is already off."
        if not powered_on:
            return "TV is already off (standby)."
        try:
            _send_key("KEY_POWER")
        except Exception as e:
            return f"Failed to send power-off: {e}"
        time.sleep(3)
        info = _rest_info(ip)
        if info is None or info.get("device", {}).get("PowerState") != "on":
            return "TV is off."
        return "Sent power-off, but the TV still reports on — it may show a confirmation prompt."


@mcp.tool()
def tv_send_keys(keys: str, delay: float = 0.7) -> str:
    """
    Send remote-control key presses to the TV (it must be on).

    Args:
        keys: One or more keys, space- or comma-separated. Friendly names:
              up, down, left, right, enter, back, exit, home, menu, source,
              play, pause, stop, rewind, fast_forward, volume_up, volume_down,
              mute, channel_up, channel_down, guide, info, 0-9, red/green/
              yellow/blue. Raw Samsung codes (KEY_*) also accepted.
              Example: "home" or "down down right enter".
        delay: Seconds to wait between keys (default 0.7).
    """
    parts = [p for p in re.split(r"[,\s]+", keys.strip()) if p]
    if not parts:
        return "No keys given."
    resolved = []
    for p in parts:
        low = p.lower()
        if low in KEY_ALIASES:
            resolved.append(KEY_ALIASES[low])
        elif p.upper().startswith("KEY_"):
            resolved.append(p.upper())
        else:
            return f"Unknown key '{p}'. Use a friendly name or a raw KEY_* code."
    try:
        for i, key in enumerate(resolved):
            _send_key(key)
            if i < len(resolved) - 1:
                time.sleep(delay)
        return f"Sent: {' '.join(resolved)}"
    except Exception as e:
        return f"Failed to send keys: {e} (is the TV on?)"


@mcp.tool()
def tv_list_apps() -> str:
    """
    List the apps installed on the TV with their IDs (TV must be on).
    Can be slow — only needed when tv_launch_app doesn't know an app.
    """
    try:
        apps = _with_remote(lambda r: r.app_list())
    except Exception:
        apps = None
    if not apps:
        known = "\n".join(f"[{v}] {k}" for k, v in KNOWN_APPS.items())
        return ("TV didn't return its app list (unsupported on some firmware). "
                f"Known launchable apps:\n{known}")
    return "\n".join(f"[{a.get('appId')}] {a.get('name')}" for a in apps)


@mcp.tool()
def tv_launch_app(app: str) -> str:
    """
    Launch an app on the TV by name or exact app ID.
    If the TV is off it is woken first (adds ~10-25s).

    Args:
        app: App name like "Netflix", "YouTube", "Disney+" — or a numeric app ID.
    """
    query = app.strip()
    q = query.lower()
    if query.isdigit():
        app_id, label = query, query
    elif q in KNOWN_APPS:
        app_id, label = KNOWN_APPS[q], query
    else:
        # Unknown name — ask the TV for its installed list (slower, and
        # unsupported on some firmware).
        try:
            apps = _with_remote(lambda r: r.app_list()) or []
        except Exception:
            apps = []
        exact = [a for a in apps if a.get("name", "").lower() == q]
        partial = [a for a in apps if q in a.get("name", "").lower()]
        match = (exact or partial or [None])[0]
        if not match:
            avail = ", ".join(a.get("name", "?") for a in apps[:30]) or ", ".join(KNOWN_APPS)
            return f"App '{app}' not found. Available: {avail}"
        app_id, label = match["appId"], match["name"]
    woke, err = _ensure_on()
    if err:
        return err
    prefix = "Turned the TV on. " if woke else ""
    # HTTP launch first (fast, no pairing); WebSocket run_app as fallback.
    # Neither reports failure honestly (a bad ID "succeeds" silently), so
    # verify by polling the app's `visible` flag before claiming success.
    ip = _load_cached_ip()
    try:
        _rest_app(ip, app_id, "POST")
    except Exception:
        try:
            _with_remote(lambda r: r.run_app(app_id))
        except Exception as e:
            return f"{prefix}Failed to launch {label}: {e}"
    # Fresh boots load apps slower, so allow extra time after a wake.
    deadline = time.time() + (15 if woke else 8)
    while time.time() < deadline:
        time.sleep(1)
        try:
            if _rest_app(ip, app_id).get("visible"):
                return f"{prefix}Launched {label} (confirmed on screen)."
        except Exception:
            pass
    return (f"{prefix}Sent launch for {label}, but it hasn't taken the screen "
            "(it may still be loading, or the app ID may be wrong for this TV).")


@mcp.tool()
def tv_type_text(text: str, submit: bool = False) -> str:
    """
    Type text into the TV's currently-focused input field (a text box with
    the on-screen keyboard up). Works with SYSTEM keyboards (Smart Hub
    search, the web browser); some apps draw their own keyboard and won't
    receive it. Faster and more reliable than arrow-keying the keyboard.

    Args:
        text: The text to type.
        submit: Also commit the input (closes the keyboard on most firmware).
                You may still need tv_send_keys("enter") to trigger a search.
    """
    try:
        _send_text(text)
        if submit:
            time.sleep(0.5)
            _send_text_end()
        return f"Typed: {text!r}" + (" (committed)" if submit else "")
    except Exception as e:
        return f"Failed to type: {e} (is a text field focused on screen?)"


@mcp.tool()
def tv_open_url(url: str) -> str:
    """
    Open a web page in the TV's built-in browser.
    Useful for putting any web-renderable content on the screen.
    If the TV is off it is woken first (adds ~10-25s).

    Args:
        url: Full URL, e.g. "https://example.com".
    """
    woke, err = _ensure_on()
    if err:
        return err
    prefix = "Turned the TV on. " if woke else ""
    try:
        _with_remote(lambda r: r.open_browser(url))
        return f"{prefix}Opened {url} in the TV browser."
    except Exception as e:
        return f"{prefix}Failed to open URL: {e}"


@mcp.tool()
def tv_set_input(source: str) -> str:
    """
    Switch the TV input. If the TV is off it is woken first (adds ~10-25s).

    This TV can't address HDMI ports directly: "hdmi" switches to HDMI and
    each further press cycles ports, so "hdmi2" is best-effort (2 presses).
    Selecting a port wakes CEC-enabled devices on it (e.g. a game console).
    To get back to apps from an input, launch an app or send "home".

    Args:
        source: One of: tv, hdmi, hdmi1, hdmi2.
    """
    entry = INPUT_KEYS.get(source.lower().strip())
    if not entry:
        return f"Unknown source '{source}'. Options: {', '.join(INPUT_KEYS)}"
    key, presses = entry
    woke, err = _ensure_on()
    if err:
        return err
    prefix = "Turned the TV on. " if woke else ""
    try:
        for i in range(presses):
            if i:
                time.sleep(2)  # let the first switch land before cycling on
            _send_key(key)
        note = " (best-effort: port cycling, can't confirm which HDMI)" if presses > 1 else ""
        return f"{prefix}Switched input to {source}.{note}"
    except Exception as e:
        return f"{prefix}Failed: {e}"


@mcp.tool()
def tv_set_volume(volume: int) -> str:
    """
    Set the TV volume to an absolute level.

    Args:
        volume: 0-100.
    """
    ip = _tv_ip()
    volume = max(0, min(100, volume))
    try:
        _upnp_volume(ip, "SetVolume", volume)
        return f"Volume set to {volume}."
    except Exception as e:
        return (f"Absolute volume failed ({e}); "
                "falling back is possible via tv_send_keys('volume_up'/'volume_down').")


if __name__ == "__main__":
    import logging
    logging.getLogger("mcp.server").setLevel(logging.WARNING)
    mcp.run(transport="stdio")
