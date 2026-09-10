"""Inbound callback listener.

The voice service is otherwise outbound-only (it POSTs text to the brain's
/api/inference). This is the one inbound surface, two endpoints:
  /speak — after a long task finishes in the background, the brain POSTs the
           result here and the main loop speaks it.
  /wake  — the brain asks for a wake-word-equivalent activation (e.g. the watch
           gesture remote sent voice_activate); the idle loop starts listening.

Stdlib-only HTTP server in a daemon thread. Single local client (the brain), so
a tiny threaded server is plenty. Auth: bearer == the shared 'voice-api-key'.
"""

import hmac
import json
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, keychain

# Results the brain pushed back, waiting for the main loop to speak them at a
# safe point (when idle, so we never talk over an active turn). Each item is
# {"text": str, "music_touched": bool} — the flag means the backgrounded task
# changed music playback, so the speaker must release its pause/resume claim.
announcements: "queue.Queue[dict]" = queue.Queue()

# External wake request: monotonic timestamp of the last /wake POST, consumed
# by wake_requested(). Timestamped rather than a bare flag so a wake that
# arrives mid-conversation can't fire minutes later when the loop next idles.
_wake_lock = threading.Lock()
_wake_at: float | None = None


def wake_requested(max_age: float = 3.0) -> bool:
    """True (once) if a /wake arrived within the last max_age seconds.
    Consumes the request either way — stale wakes are dropped, not queued."""
    global _wake_at
    with _wake_lock:
        at, _wake_at = _wake_at, None
    return at is not None and (time.monotonic() - at) <= max_age


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802 (stdlib naming)
        path = self.path.rstrip("/")
        if path not in ("/speak", "/wake"):
            self._send(404, {"error": "not found"})
            return

        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        try:
            expected = keychain.get_secret(config.BRAIN_API_KEY_SERVICE)
        except Exception:
            self._send(500, {"error": "no key"})
            return
        if not hmac.compare_digest(token, expected):
            self._send(401, {"error": "unauthorized"})
            return

        if path == "/wake":
            global _wake_at
            with _wake_lock:
                _wake_at = time.monotonic()
            print("  [callback] wake requested")
            self._send(200, {"ok": True})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._send(400, {"error": "bad json"})
            return

        text = (data.get("text") or "").strip()
        if text:
            announcements.put({"text": text, "music_touched": bool(data.get("music_touched"))})
        self._send(200, {"ok": True})

    def log_message(self, *args):  # silence default stderr access logging
        pass


def start() -> None:
    """Start the callback listener in a daemon thread. Best-effort: if the port
    is taken, the voice service still works (it just won't receive async results)."""
    try:
        srv = ThreadingHTTPServer((config.CALLBACK_HOST, config.CALLBACK_PORT), _Handler)
    except OSError as e:
        print(f"  [callback] could NOT start on {config.CALLBACK_HOST}:{config.CALLBACK_PORT} ({e}) "
              "— async results won't be delivered")
        return
    threading.Thread(target=srv.serve_forever, name="voice-callback", daemon=True).start()
    print(f"  [callback] listening on {config.CALLBACK_HOST}:{config.CALLBACK_PORT}")
