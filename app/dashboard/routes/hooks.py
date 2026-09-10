"""Webhook ingress — the public face of webhook triggers.

POST /hooks/<name> fires the named trigger. No dashboard session auth: callers
are machines (iOS Shortcuts, other tailnet devices/services), authenticated by
the trigger's own secret — header `X-Hook-Secret: <secret>` or, for clients
that can't set headers, `?secret=<secret>`.

The response returns immediately ('accepted'/'debounced'/'disabled'); the
action itself runs in a background task inside the trigger engine, so a
Shortcut never hangs on an LLM. `?test=1` bypasses debounce (manual testing).
"""

import hmac

from quart import Blueprint, request, jsonify, current_app

import trigger_store

hooks_bp = Blueprint("hooks", __name__)


@hooks_bp.route("/hooks/<name>", methods=["POST"])
async def fire_hook(name):
    trigger = trigger_store.get_trigger(name)
    if not trigger:
        return jsonify({"error": "unknown trigger"}), 404

    provided = (request.headers.get("X-Hook-Secret")
                or request.args.get("secret", "") or "")
    expected = (trigger.get("source") or {}).get("secret") or ""
    if not expected or not hmac.compare_digest(provided, expected):
        return jsonify({"error": "unauthorized"}), 401

    payload = await request.get_json(silent=True) or {}
    source = "test" if request.args.get("test") == "1" else "webhook"
    status = current_app.trigger_engine.accept(trigger, payload, source)
    return jsonify({"status": status})
