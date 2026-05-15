"""
STT (Speech-to-Text) service — transcribes audio via mlx-whisper on Apple Silicon GPU.

Standalone service that can be used by any interface (watch, dashboard, telegram, etc.).
Runs as a persistent HTTP server so the model stays loaded in memory.

Usage:
    python stt.py                  # start server on port 7863
    curl -X POST http://127.0.0.1:7863/transcribe -F "audio=@recording.wav"
"""

import asyncio
import json
import os
import subprocess
import tempfile
import time
import uuid
import urllib.request
import urllib.error
from pathlib import Path

SERVER_URL = "http://127.0.0.1:7863"
VENV_PYTHON = str(Path(__file__).resolve().parents[2] / "venv" / "bin" / "python")

_server_process = None


def _server_healthy() -> bool:
    try:
        req = urllib.request.Request(f"{SERVER_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except (urllib.error.URLError, OSError):
        return False


async def ensure_server():
    """Start the STT server if it's not already running."""
    global _server_process

    if _server_healthy():
        return True

    print("  [stt] Starting Whisper STT server...")
    _server_process = subprocess.Popen(
        [VENV_PYTHON, __file__, "--serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(60):
        await asyncio.sleep(1)
        if _server_healthy():
            print("  [stt] Server ready.")
            return True

    print("  [stt] Server failed to start.")
    return False


async def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str | None:
    """
    Transcribe audio bytes to text. Starts the server if needed.
    Returns transcribed text or None on failure.
    """
    if not await ensure_server():
        return None

    def _request():
        boundary = uuid.uuid4().hex
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + audio_bytes + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"{SERVER_URL}/transcribe",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    try:
        result = await asyncio.get_event_loop().run_in_executor(None, _request)
        return result.get("text", "").strip()
    except Exception as e:
        print(f"  [stt] Transcription failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Server mode — run with --serve
# ---------------------------------------------------------------------------

def _parse_multipart(rfile, content_type, content_length) -> bytes:
    """Parse multipart form data and extract the audio file bytes."""
    boundary = content_type.split("boundary=")[1].strip()
    raw = rfile.read(content_length)

    # Split on boundary, find the audio part
    parts = raw.split(f"--{boundary}".encode())
    for part in parts:
        if b"name=\"audio\"" in part:
            # Skip headers (separated from body by \r\n\r\n)
            header_end = part.find(b"\r\n\r\n")
            if header_end != -1:
                return part[header_end + 4:].rstrip(b"\r\n")
    return raw  # fallback: treat entire body as audio


def _run_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler

    model = None
    MODEL_NAME = "mlx-community/whisper-small-mlx"

    def get_model():
        nonlocal model
        if model is None:
            print("[stt] Loading Whisper model...")
            t0 = time.time()
            import mlx_whisper
            # Warm up: create a short silent WAV to force model load
            import struct, wave
            warmup_path = os.path.join(tempfile.gettempdir(), "stt_warmup.wav")
            with wave.open(warmup_path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(struct.pack("<" + "h" * 16000, *([0] * 16000)))
            mlx_whisper.transcribe(
                warmup_path,
                path_or_hf_repo=MODEL_NAME,
                language="en",
            )
            os.unlink(warmup_path)
            model = mlx_whisper
            print(f"[stt] Model loaded in {time.time() - t0:.1f}s")
        return model

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # silence request logs

        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')

        def do_POST(self):
            if self.path != "/transcribe":
                self.send_response(404)
                self.end_headers()
                return

            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))

            if "multipart/form-data" in content_type:
                audio_data = _parse_multipart(self.rfile, content_type, content_length)
            else:
                audio_data = self.rfile.read(content_length)

            # Write to temp file for whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                tmp_path = f.name

            try:
                t0 = time.time()
                whisper = get_model()
                result = whisper.transcribe(
                    tmp_path,
                    path_or_hf_repo=MODEL_NAME,
                    language="en",
                )
                elapsed = time.time() - t0
                text = result.get("text", "").strip()
                print(f"[stt] Transcribed in {elapsed:.2f}s: {text[:80]}")

                response = json.dumps({"text": text, "duration": elapsed}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-Transcription-Time", f"{elapsed:.2f}")
                self.end_headers()
                self.wfile.write(response)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            finally:
                os.unlink(tmp_path)

    # Pre-load model
    get_model()

    server = HTTPServer(("127.0.0.1", 7863), Handler)
    print("[stt] Listening on http://127.0.0.1:7863")
    server.serve_forever()


if __name__ == "__main__":
    import sys
    if "--serve" in sys.argv:
        _run_server()
    else:
        # Quick test
        print("Starting STT server...")
        _run_server()
