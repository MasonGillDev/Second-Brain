"""Voice API endpoint — simple REST for the voice menu bar app."""

import hmac
from quart import Blueprint, request, jsonify, current_app
from keychain import get_secret
from interfaces.tts import generate_speech_audio
from interfaces.stt import transcribe

voice_bp = Blueprint("voice", __name__)


def _check_local_auth():
    """Verify bearer token for local voice app requests."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    try:
        expected = get_secret("voice-api-key")
    except RuntimeError:
        return False
    return hmac.compare_digest(token, expected)


@voice_bp.route("/api/voice", methods=["POST"])
async def voice():
    """
    Accept audio or text, process through agent, return response + TTS audio.

    Request JSON:
        - audio_b64 (str, optional): base64-encoded audio to transcribe
        - text (str, optional): pre-transcribed text (skips STT)

    Response JSON:
        - text (str): agent response
        - transcribed (str): what the user said (if audio was sent)
        - audio_url (str|null): TTS audio file URL
    """
    if not _check_local_auth():
        return jsonify({"error": "unauthorized"}), 401

    data = await request.get_json()
    user_text = data.get("text", "").strip()

    # Transcribe audio if provided
    if not user_text and data.get("audio_b64"):
        import base64
        audio_bytes = base64.b64decode(data["audio_b64"])
        user_text = await transcribe(audio_bytes) or ""

    if not user_text:
        return jsonify({"error": "no input"}), 400

    # Process through agent with voice mode
    agent = current_app.agent
    response_text = await agent.process(user_text, source="voice")

    # Generate TTS
    audio_url = None
    filename = await generate_speech_audio(response_text)
    if filename:
        audio_url = f"http://127.0.0.1:5001/static/audio/{filename}"

    return jsonify({
        "text": response_text,
        "transcribed": user_text,
        "audio_url": audio_url,
    })
