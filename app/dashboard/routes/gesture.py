"""Gesture endpoint — the Apple Watch gesture remote POSTs detected gestures
here; the hub owns what each gesture actually does.

Phase 1 implements voice_activate (wake the voice assistant as if the wake
word was heard). The remaining spec gestures are accepted and logged so the
watch app can be built and tested before their handlers exist.
"""

import hmac

from quart import Blueprint, request, jsonify

import delivery
from keychain import get_secret

gesture_bp = Blueprint("gesture", __name__)

# Full gesture vocabulary from the watch spec. Handlers are filled in as the
# hub side of each gesture is built; None = accepted but not implemented yet.
_HANDLERS: dict[str, object] = {
    "voice_activate": delivery.send_voice_wake,
    "brightness_up": None,
    "brightness_down": None,
    "prev_track": None,
    "next_track": None,
    "play_pause": None,
}


def _check_auth() -> str | None:
    """Validate Bearer token (same key as the iOS/watch clients). Returns an
    error message or None if OK."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return "unauthorized"
    try:
        correct = get_secret("watch-api-key")
    except RuntimeError:
        return "watch-api-key not configured"
    if not hmac.compare_digest(auth[7:], correct):
        return "unauthorized"
    return None


@gesture_bp.route("/api/gesture", methods=["POST"])
async def gesture():
    """Dispatch a gesture. The watch fires and forgets — respond fast, never
    block on downstream work longer than the handler itself needs."""
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401

    data = await request.get_json(silent=True)
    name = ((data or {}).get("gesture") or "").strip()
    if name not in _HANDLERS:
        return jsonify({"error": f"unknown gesture '{name}'"}), 400

    handler = _HANDLERS[name]
    if handler is None:
        print(f"  [gesture] {name}: no handler yet")
        return jsonify({"ok": True, "handled": False})

    print(f"  [gesture] {name}")
    ok = await handler()
    return jsonify({"ok": ok, "handled": True})
