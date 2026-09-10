"""Text inference endpoint — text in, text out, with async hand-off for slow work.

The brain's only voice-facing surface. The standalone voice assistant service
(wake word -> STT -> TTS) does all audio work locally and only exchanges text
with this endpoint. Authenticated with the local 'voice-api-key' bearer token.

Hybrid timing model (so voice isn't blocked on minutes-long Claude Code tasks):
  - The request races agent.process() against VOICE_RESPONSE_DEADLINE.
  - Finishes in time  -> return the answer synchronously (quick commands, as before).
  - Runs over          -> return a short spoken ack now, let the task finish in the
                          background, and push its result (or the system_admin
                          CONFIRMATION question) to the voice service's callback
                          listener when it's ready.
Only one job runs at a time; an overlapping request gets a 'still working' ack.
"""

import asyncio
import hmac

from quart import Blueprint, request, jsonify, current_app
from keychain import get_secret
from delivery import post_voice_blocking as _post_to_voice
import config

inference_bp = Blueprint("inference", __name__)

# Spoken immediately when a turn is too slow to answer inline; the real answer
# follows later via the callback listener.
_WORKING_ACK = "Okay, I'm on it — I'll let you know when it's ready."
# Spoken when a background job is still running and a new request comes in.
_BUSY_ACK = "I'm still working on the last thing — give me a moment."

# Playback-state-changing music tools. If the agent calls one of these during a
# turn, the response carries music_touched=True so the voice service releases
# its pause/resume claim on the music (the user's expressed intent — "pause the
# music", "play something" — now owns that state, and the voice service must not
# auto-resume over it when the conversation ends).
_MUSIC_STATE_TOOLS = {
    "music__play", "music__pause", "music__resume", "music__skip",
    "music__previous", "music__play_playlist",
}


def _check_local_auth() -> bool:
    """Verify bearer token for local inference requests."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    try:
        expected = get_secret("voice-api-key")
    except RuntimeError:
        return False
    return hmac.compare_digest(token, expected)


@inference_bp.route("/api/inference", methods=["POST"])
async def inference():
    """Run text through the agent. Returns quickly with either the full answer
    (status 'complete') or an ack (status 'working'/'busy').

    Request JSON:  {"text": "<user text>"}
    Response JSON: {"text": "<spoken text>", "status": "complete|working|busy|error"}
    """
    if not _check_local_auth():
        return jsonify({"error": "unauthorized"}), 401

    data = await request.get_json()
    text = (data or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "no input"}), 400

    agent = current_app.agent

    # One job at a time: a backgrounded task owns the agent until it finishes.
    if agent.is_busy():
        return jsonify({"text": _BUSY_ACK, "status": "busy"})

    holder: dict = {}
    tools_used: list[str] = []

    async def _work():
        agent.on_tool_call = lambda name, args: tools_used.append(name)
        try:
            holder["result"] = await agent.process(text, source="voice")
        except Exception as e:  # noqa: BLE001 — surface as spoken error, don't 500
            holder["error"] = e
        finally:
            agent.on_tool_call = None

    def _music_touched() -> bool:
        return any(name in _MUSIC_STATE_TOOLS for name in tools_used)

    task = asyncio.ensure_future(_work())
    deadline = float(getattr(config, "VOICE_RESPONSE_DEADLINE", 10))
    done, _pending = await asyncio.wait({task}, timeout=deadline)

    if task in done:
        # Finished within the deadline — answer synchronously, exactly as before.
        if "error" in holder:
            print(f"  [voice] inference error: {holder['error']}")
            return jsonify({"text": "Sorry, that ran into an error.", "status": "error"})
        return jsonify({"text": holder.get("result", ""), "status": "complete",
                        "music_touched": _music_touched(),
                        "thread": agent.last_thread_event})

    # Too slow — finish in the background and speak the result when it's ready.
    async def _deliver():
        await task
        if "error" in holder:
            print(f"  [voice] background task error: {holder['error']}")
            msg = "Sorry, that task ran into a problem before it finished."
        else:
            msg = holder.get("result", "") or "That's done."
        await asyncio.to_thread(_post_to_voice, msg, _music_touched())

    current_app.add_background_task(_deliver)
    return jsonify({"text": _WORKING_ACK, "status": "working"})
