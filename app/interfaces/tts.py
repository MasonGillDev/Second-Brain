"""
TTS post-processing — generates speech audio via a persistent Kokoro server.

Interface layer utility. Not an agent tool — the agent never sees this.
The Kokoro model stays loaded in a background process so generation is fast (~1-2s).
"""

import asyncio
import json
import uuid
import os
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

KOKORO_DIR = Path.home() / "TTSKokomo" / "Kokoro-TTS-Local"
KOKORO_PYTHON = str(KOKORO_DIR / "venv" / "bin" / "python")
SERVER_URL = "http://127.0.0.1:7862"
AUDIO_DIR = Path(__file__).parent.parent / "dashboard" / "static" / "audio"

VOICE = "af_heart"
SPEED = 1.0
LANG = "a"

_server_process = None


def _server_healthy() -> bool:
    """Check if the TTS server is running."""
    try:
        req = urllib.request.Request(f"{SERVER_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except (urllib.error.URLError, OSError):
        return False


async def _ensure_server():
    """Start the TTS server if it's not already running."""
    global _server_process

    if _server_healthy():
        return True

    print("  [tts] Starting Kokoro TTS server...")
    _server_process = subprocess.Popen(
        [KOKORO_PYTHON, "tts_server.py"],
        cwd=str(KOKORO_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for it to become healthy (model loading takes a few seconds)
    for _ in range(30):
        await asyncio.sleep(1)
        if _server_healthy():
            print("  [tts] Server ready.")
            return True

    print("  [tts] Server failed to start.")
    return False


async def generate_speech_audio(
    text: str,
    voice: str = VOICE,
    speed: float = SPEED,
    lang: str = LANG,
) -> str | None:
    """
    Generate a wav file from text. Returns the filename (not full path),
    or None on failure. The file is written to dashboard/static/audio/.
    """
    if not await _ensure_server():
        return None

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex[:12]}.wav"
    out_path = str(AUDIO_DIR / filename)

    payload = json.dumps({
        "text": text,
        "voice": voice,
        "speed": max(0.5, min(2.0, speed)),
        "lang": lang,
    }).encode()

    def _request():
        req = urllib.request.Request(
            f"{SERVER_URL}/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            gen_time = resp.headers.get("X-Generation-Time", "?")
            print(f"  [tts] Generated in {gen_time}s")
            with open(out_path, "wb") as f:
                f.write(resp.read())

    def _cleanup_old_audio():
        existing = sorted(AUDIO_DIR.glob("*.wav"), key=lambda p: p.stat().st_mtime)
        for old_file in existing[:-3]:
            old_file.unlink(missing_ok=True)

    try:
        await asyncio.get_event_loop().run_in_executor(None, _request)
        asyncio.get_event_loop().run_in_executor(None, _cleanup_old_audio)
        return filename
    except Exception as e:
        print(f"  [tts] Generation failed: {e}")
        return None
