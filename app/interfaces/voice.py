"""
Voice Interface — macOS menu bar app with push-to-talk.

Hold Right Option key to record, release to send.
Records mic → STT → Agent (voice mode) → TTS → speaker.

Started automatically by the dashboard server.
"""

import base64
import io
import json
import os
import struct
import sys
import threading
import time
import wave
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rumps
import sounddevice as sd
import numpy as np
from Quartz import (
    CGEventMaskBit, kCGEventFlagsChanged, kCGEventFlagMaskAlternate,
    CGEventGetFlags, CGEventGetIntegerValueField,
    CGEventTapCreate, kCGSessionEventTap, kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly, CFMachPortCreateRunLoopSource,
    CFRunLoopGetCurrent, CFRunLoopAddSource, kCFRunLoopDefaultMode,
    CFRunLoopRun, kCGKeyboardEventKeycode,
)
from keychain import get_secret

# ── Config ──────────────────────────────────────────────────────────
DASHBOARD_URL = "http://127.0.0.1:5001"
SAMPLE_RATE = 16000
CHANNELS = 1
RIGHT_OPTION_KEYCODE = 61  # Right Option key

# ── Trigger Layer ───────────────────────────────────────────────────
# Currently: push-to-talk via global hotkey.
# Future: add a WakeWordTrigger class that listens for a wake word
# and calls the same on_trigger_start / on_trigger_stop callbacks.
# The pipeline doesn't care what started the recording.


class VoiceApp(rumps.App):
    def __init__(self):
        super().__init__("🎙️", quit_button="Quit")
        self._api_key = get_secret("voice-api-key")
        self._recording = False
        self._audio_frames = []
        self._stream = None

        # Menu items
        self._status_item = rumps.MenuItem("Ready — hold Right ⌥ to talk")
        self._status_item.set_callback(None)
        self.menu = [self._status_item]

        # Start global hotkey listener in background
        self._hotkey_thread = threading.Thread(target=self._listen_hotkey, daemon=True)
        self._hotkey_thread.start()

    # ── Recording ───────────────────────────────────────────────────

    def _start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._audio_frames = []
        self._set_status("recording", "Recording...")

        def audio_callback(indata, frames, time_info, status):
            if self._recording:
                self._audio_frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=audio_callback,
        )
        self._stream.start()

    def _stop_recording(self):
        if not self._recording:
            return
        self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._audio_frames:
            self._set_status("idle", "Ready — hold Right ⌥ to talk")
            return

        audio_data = np.concatenate(self._audio_frames)
        self._set_status("processing", "Processing...")

        # Process in background so we don't block the event tap
        threading.Thread(target=self._process_audio, args=(audio_data,), daemon=True).start()

    # ── Pipeline ────────────────────────────────────────────────────

    def _process_audio(self, audio_data: np.ndarray):
        """Send audio through the full pipeline: STT → Agent → TTS → play."""
        try:
            # Encode as WAV
            wav_b64 = self._encode_wav_b64(audio_data)

            # Send to dashboard voice endpoint (handles STT + agent + TTS)
            self._set_status("processing", "Thinking...")
            result = self._call_voice_api(wav_b64)

            if not result:
                self._set_status("idle", "Ready — hold Right ⌥ to talk")
                return

            transcribed = result.get("transcribed", "")
            response = result.get("text", "")
            audio_url = result.get("audio_url")

            print(f"  [voice] You: {transcribed}")
            print(f"  [voice] Agent: {response[:100]}")

            # Play TTS audio
            if audio_url:
                self._set_status("speaking", "Speaking...")
                self._play_audio(audio_url)

            self._set_status("idle", "Ready — hold Right ⌥ to talk")

        except Exception as e:
            print(f"  [voice] Error: {e}")
            self._set_status("idle", f"Error: {str(e)[:40]}")
            time.sleep(3)
            self._set_status("idle", "Ready — hold Right ⌥ to talk")

    def _encode_wav_b64(self, audio_data: np.ndarray) -> str:
        """Encode int16 numpy audio as base64 WAV."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # int16
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _call_voice_api(self, audio_b64: str) -> dict | None:
        """POST to the dashboard voice endpoint."""
        payload = json.dumps({"audio_b64": audio_b64}).encode()
        req = urllib.request.Request(
            f"{DASHBOARD_URL}/api/voice",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  [voice] API error {e.code}: {body}")
            return None
        except urllib.error.URLError as e:
            print(f"  [voice] Connection error: {e}")
            return None

    def _play_audio(self, audio_url: str):
        """Download and play a WAV file."""
        try:
            req = urllib.request.Request(audio_url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                audio_bytes = resp.read()

            buf = io.BytesIO(audio_bytes)
            with wave.open(buf, "rb") as wf:
                rate = wf.getframerate()
                channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())
                dtype = {1: "int8", 2: "int16", 4: "int32"}.get(wf.getsampwidth(), "int16")

            audio_array = np.frombuffer(frames, dtype=dtype)
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)

            sd.play(audio_array, samplerate=rate)
            sd.wait()
        except Exception as e:
            print(f"  [voice] Audio playback error: {e}")

    # ── Status ──────────────────────────────────────────────────────

    def _set_status(self, state: str, text: str):
        icons = {"idle": "🎙️", "recording": "🔴", "processing": "⏳", "speaking": "🔊"}
        self.icon = None
        self.title = icons.get(state, "🎙️")
        self._status_item.title = text

    # ── Global Hotkey (Right Option) ────────────────────────────────

    def _listen_hotkey(self):
        """Monitor global key events for Right Option hold/release."""
        self._right_opt_held = False

        def callback(proxy, event_type, event, refcon):
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            flags = CGEventGetFlags(event)
            alt_down = bool(flags & kCGEventFlagMaskAlternate)

            if keycode == RIGHT_OPTION_KEYCODE:
                if alt_down and not self._right_opt_held:
                    self._right_opt_held = True
                    self._start_recording()
                elif not alt_down and self._right_opt_held:
                    self._right_opt_held = False
                    self._stop_recording()

            return event

        mask = CGEventMaskBit(kCGEventFlagsChanged)
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            mask,
            callback,
            None,
        )

        if tap is None:
            print("  [voice] ERROR: Could not create event tap.")
            print("  [voice] Grant Accessibility permissions in System Settings → Privacy & Security → Accessibility")
            return

        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopDefaultMode)
        CFRunLoopRun()


if __name__ == "__main__":
    VoiceApp().run()
