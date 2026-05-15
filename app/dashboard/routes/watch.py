"""Watch REST API endpoint — simple bearer-token auth for the Apple Watch app."""

import hmac
from quart import Blueprint, request, jsonify, current_app
from keychain import get_secret
from interfaces.stt import transcribe

watch_bp = Blueprint("watch", __name__)


def _check_auth() -> str | None:
    """Validate Bearer token. Returns error message or None if OK."""
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


@watch_bp.route("/api/watch/chat", methods=["POST"])
async def watch_chat():
    """Accept text, run agent, return response."""
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401

    data = await request.get_json()
    if not data or not data.get("text", "").strip():
        return jsonify({"error": "missing text"}), 400

    text = data["text"].strip()
    print(f"  [watch] Received: {text}")

    try:
        agent = current_app.agent
        response_text = await agent.process(text, source="watch")
        print(f"  [watch] Response: {response_text[:100]}")
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@watch_bp.route("/api/watch/voice", methods=["POST"])
async def watch_voice():
    """Accept audio, transcribe, run agent, return response."""
    err = _check_auth()
    if err:
        return jsonify({"error": err}), 401

    files = await request.files
    audio_file = files.get("audio")
    if not audio_file:
        return jsonify({"error": "missing audio"}), 400

    audio_bytes = audio_file.read()
    print(f"  [watch] Received audio: {len(audio_bytes)} bytes")

    # Transcribe
    text = await transcribe(audio_bytes, filename=audio_file.filename or "audio.wav")
    if not text:
        return jsonify({"error": "transcription failed"}), 500

    print(f"  [watch] Transcribed: {text}")

    # Run agent
    try:
        agent = current_app.agent
        response_text = await agent.process(text, source="watch")
        print(f"  [watch] Response: {response_text[:100]}")
        return jsonify({"transcript": text, "response": response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
