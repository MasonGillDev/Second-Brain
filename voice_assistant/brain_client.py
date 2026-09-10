"""Client for the dashboard's text inference endpoint (text in, text out)."""

import requests

from . import config, keychain


def ask(text: str) -> tuple[str, str, bool, dict | None]:
    """Send transcribed text to the brain. Returns
    (reply_text, status, music_touched, thread):
      - 'complete' : an inline answer (speak it, continue the conversation)
      - 'working'  : the turn went async — the real answer arrives later via the
                     callback, so there's nothing more to wait for this turn
      - 'busy'     : a prior task is still running; this request was declined
    music_touched is True when the agent changed music playback this turn (the
    voice service must then release its pause/resume claim on the music).
    thread is the brain's thread event ({"event": "resumed"|"new", "title": ...})
    or None — used to speak the "picking up our conversation about X" cue.
    """
    key = keychain.get_secret(config.BRAIN_API_KEY_SERVICE)
    resp = requests.post(
        config.DASHBOARD_URL + config.INFERENCE_PATH,
        json={"text": text},
        headers={"Authorization": f"Bearer {key}"},
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return (data.get("text", ""), data.get("status", "complete"),
            bool(data.get("music_touched")), data.get("thread"))
