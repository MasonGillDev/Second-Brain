"""
Document ingest upload endpoint.

Accepts file uploads from trusted devices (PC, MacBook) over Tailscale/LAN and
drops them into DOCS_DIR, then runs ingestion immediately so the file is
searchable right away. This is the landing point for the folder-watcher client
that runs on each device.

Authenticated with the 'ingest-api-key' bearer token (macOS Keychain).
"""

import asyncio
import hmac
import os
import re

from quart import Blueprint, request, jsonify, current_app
from keychain import get_secret
from memory.ingestion import ingest_documents, SUPPORTED_EXTENSIONS
from dashboard.auth import require_auth
import config
import device_store

ingest_bp = Blueprint("ingest", __name__)

# Ingestion re-scans the whole docs dir; serialize concurrent uploads so two
# devices landing files at once don't race on the ChromaDB writes.
_ingest_lock = asyncio.Lock()


def _check_auth() -> bool:
    """Verify the ingest bearer token."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    try:
        expected = get_secret("ingest-api-key")
    except RuntimeError:
        return False
    return bool(token) and hmac.compare_digest(token, expected)


def _safe_filename(name: str) -> str:
    """Reduce an arbitrary uploaded name to a safe basename inside DOCS_DIR."""
    name = os.path.basename(name or "").replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip()
    # Guard against names that collapse to nothing or hidden/traversal forms.
    if name in ("", ".", ".."):
        return ""
    return name


@ingest_bp.route("/api/ingest/upload", methods=["POST"])
async def upload():
    """Receive one file (multipart field 'file'), save it to DOCS_DIR, and
    ingest immediately.

    Response JSON: {"status": "ok", "file": "<name>", "chunks_added": <int>}
    chunks_added is 0 when the file is byte-identical to one already ingested.
    """
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401

    files = await request.files
    f = files.get("file")
    if f is None:
        return jsonify({"error": "no file provided (multipart field 'file')"}), 400

    filename = _safe_filename(f.filename)
    if not filename:
        return jsonify({"error": "invalid filename"}), 400

    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return jsonify({
            "error": f"unsupported file type '{ext}'",
            "supported": sorted(SUPPORTED_EXTENSIONS),
        }), 415

    os.makedirs(config.DOCS_DIR, exist_ok=True)
    dest = os.path.join(config.DOCS_DIR, filename)

    data = f.read()  # werkzeug FileStorage.read() -> bytes
    if asyncio.iscoroutine(data):  # Quart's FileStorage may make this async
        data = await data
    if not data:
        return jsonify({"error": "empty file"}), 400

    async with _ingest_lock:
        await asyncio.to_thread(_write_bytes, dest, data)
        added = await asyncio.to_thread(ingest_documents, current_app.vector_store)

    # Credit the sending device (heartbeat + files_sent) if it identified itself.
    device_id = request.headers.get("X-Device-Id", "").strip()
    if device_id:
        await asyncio.to_thread(device_store.touch_device, device_id, 1)

    return jsonify({"status": "ok", "file": filename, "chunks_added": added})


@ingest_bp.route("/api/ingest/register", methods=["POST"])
async def register():
    """A watcher client announces itself on startup: hostname, platform, and the
    folders it is watching. Idempotent — safe to call on every launch."""
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401

    body = await request.get_json(silent=True) or {}
    device_id = (body.get("device_id") or "").strip().lower()
    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    await asyncio.to_thread(
        device_store.register_device,
        device_id,
        (body.get("hostname") or device_id).strip(),
        (body.get("platform") or "").strip(),
        body.get("watch_paths") or [],
    )
    return jsonify({"status": "ok", "device_id": device_id})


@ingest_bp.route("/api/ingest/heartbeat", methods=["POST"])
async def heartbeat():
    """Periodic liveness ping from a watcher client — refreshes last_seen."""
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401

    body = await request.get_json(silent=True) or {}
    device_id = (body.get("device_id") or "").strip().lower()
    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    await asyncio.to_thread(device_store.touch_device, device_id, 0)
    return jsonify({"status": "ok"})


@ingest_bp.route("/api/devices")
@require_auth
async def list_devices():
    """Dashboard-facing (session-authed) list of registered watcher devices."""
    return jsonify(await asyncio.to_thread(device_store.list_devices))


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)
