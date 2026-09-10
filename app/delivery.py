"""
Delivery sinks — route a finished piece of text to a channel.

One concern: given text and a list of sink names, deliver it. Used by the
scheduler daemon (task results), the trigger engine (trigger action results),
and the dashboard's voice hand-off. Consolidates the Telegram sends that were
previously inlined in scheduler.py / interfaces/sleep.py and the voice callback
POST from dashboard/routes/inference.py.

Sinks:
  - "telegram": Telegram Bot API sendMessage to config.TELEGRAM_NOTIFY_USER_ID
  - "voice":    POST to the voice assistant's callback listener (it speaks the
                text aloud when idle)
  - "silent":   no-op (the action's side effects were the point)

Every send is best-effort: failures are printed + logged, never raised, so a
dead sink can't take down a scheduler tick or a trigger dispatch.
"""

import asyncio
import json
import urllib.request

import config
from keychain import get_secret

VALID_SINKS = {"telegram", "voice", "silent"}

# Telegram hard-caps message length; longer results are sent in chunks.
_TELEGRAM_CHUNK = 4096


async def send_telegram(text: str) -> bool:
    """Send text to the notify user via the Telegram Bot API, chunked to the
    4096-char message limit. Returns True if every chunk was accepted."""
    import httpx

    try:
        token = get_secret("telegram-bot-token")
    except RuntimeError:
        token = None
    user_id = config.TELEGRAM_NOTIFY_USER_ID
    if not token or not user_id:
        print("  [delivery] telegram skipped: missing telegram-bot-token or TELEGRAM_NOTIFY_USER_ID")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ok = True
    try:
        async with httpx.AsyncClient() as client:
            for i in range(0, len(text), _TELEGRAM_CHUNK):
                resp = await client.post(url, json={
                    "chat_id": user_id,
                    "text": text[i:i + _TELEGRAM_CHUNK],
                })
                ok = ok and resp.status_code == 200
    except Exception as e:
        print(f"  [delivery] telegram send failed: {e}")
        return False
    return ok


def post_voice_blocking(text: str, music_touched: bool = False) -> bool:
    """Push text to the voice assistant's callback listener, which speaks it
    when idle. Blocking (stdlib urllib) — call via asyncio.to_thread from async
    code. Best-effort: if the voice service is down, log and drop."""
    try:
        key = get_secret("voice-api-key")
    except RuntimeError:
        print("  [delivery] voice skipped: no voice-api-key")
        return False
    body = json.dumps({"text": text, "music_touched": music_touched}).encode()
    req = urllib.request.Request(
        config.VOICE_CALLBACK_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=15).read()
        return True
    except Exception as e:
        print(f"  [delivery] voice delivery failed: {e}")
        return False


async def send_voice(text: str) -> bool:
    return await asyncio.to_thread(post_voice_blocking, text)


def post_voice_wake_blocking() -> bool:
    """Ask the voice assistant to start listening, as if the wake word was
    heard (used by the watch gesture remote's voice_activate). Best-effort."""
    try:
        key = get_secret("voice-api-key")
    except RuntimeError:
        print("  [delivery] voice wake skipped: no voice-api-key")
        return False
    req = urllib.request.Request(
        config.VOICE_WAKE_URL,
        data=b"{}",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5).read()
        return True
    except Exception as e:
        print(f"  [delivery] voice wake failed: {e}")
        return False


async def send_voice_wake() -> bool:
    return await asyncio.to_thread(post_voice_wake_blocking)


async def deliver(sinks: list[str], text: str) -> dict[str, bool]:
    """Deliver text to each named sink. Unknown sinks are logged and reported
    False. Never raises."""
    results: dict[str, bool] = {}
    for sink in sinks or []:
        try:
            if sink == "silent":
                results[sink] = True
            elif sink == "telegram":
                results[sink] = await send_telegram(text)
            elif sink == "voice":
                results[sink] = await send_voice(text)
            else:
                print(f"  [delivery] unknown sink '{sink}' — skipped")
                results[sink] = False
        except Exception as e:
            print(f"  [delivery] sink '{sink}' failed: {e}")
            results[sink] = False
    return results
