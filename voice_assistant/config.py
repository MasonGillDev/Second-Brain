"""Configuration for the voice assistant service. Override any value via env var."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ── The "brain" (dashboard) ──────────────────────────────────────────
# The voice service only talks text to the dashboard's inference endpoint.
DASHBOARD_URL = os.environ.get("BRAIN_URL", "http://127.0.0.1:5001")
INFERENCE_PATH = os.environ.get("BRAIN_INFERENCE_PATH", "/api/inference")
BRAIN_API_KEY_SERVICE = "voice-api-key"  # macOS Keychain service name
# The brain now always replies within its deadline (a quick answer, or an ack for
# a slow task it backgrounds), so this only needs to cover the fast path + ack.
REQUEST_TIMEOUT = 60

# ── Inbound callback (brain pushes long-task results back here) ───────
# The brain POSTs a finished background result to http://CALLBACK_HOST:CALLBACK_PORT/speak
# and the main loop speaks it. Keep in sync with the brain's VOICE_CALLBACK_URL.
CALLBACK_HOST = os.environ.get("VOICE_CALLBACK_HOST", "127.0.0.1")
CALLBACK_PORT = int(os.environ.get("VOICE_CALLBACK_PORT", "5002"))

# ── Wake word (openWakeWord) ─────────────────────────────────────────
# Pretrained options include: hey_jarvis, alexa, hey_mycroft, hey_rhasspy.
WAKE_WORD = os.environ.get("WAKE_WORD", "hey_jarvis")
WAKE_THRESHOLD = float(os.environ.get("WAKE_THRESHOLD", "0.5"))
OWW_INFERENCE_FRAMEWORK = "onnx"

# ── Audio capture ────────────────────────────────────────────────────
# Mic, wake word, and STT all run at 16 kHz mono. openWakeWord wants
# 80 ms frames (1280 samples) fed one at a time.
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_SAMPLES = 1280

# ── Utterance endpointing (Silero VAD) ───────────────────────────────
# Speech detection scores actual *speech*, so steady background noise (fan,
# AC, music bed) neither starts a phantom recording nor keeps one alive to the
# MAX_UTTERANCE cap. SILENCE_RMS remains only as the fallback gate if the VAD
# model can't load.
VAD_ENABLED = os.environ.get("VAD_ENABLED", "1") not in ("0", "false", "False")
VAD_THRESHOLD = float(os.environ.get("VAD_THRESHOLD", "0.5"))  # speech probability gate
SILENCE_RMS = float(os.environ.get("SILENCE_RMS", "450"))  # int16 RMS (fallback only)
# Adaptive endpointing: a short utterance (a command) ends after only
# SILENCE_QUICK of trailing silence so it fires fast; once you've spoken more
# than ADAPTIVE_SPEECH_CUTOFF seconds (dictation / thinking out loud) the
# tolerance grows to SILENCE_DURATION so mid-sentence pauses don't cut you off.
SILENCE_QUICK = float(os.environ.get("SILENCE_QUICK", "0.7"))
ADAPTIVE_SPEECH_CUTOFF = float(os.environ.get("ADAPTIVE_SPEECH_CUTOFF", "2.0"))
SILENCE_DURATION = float(os.environ.get("SILENCE_DURATION", "2.0"))
START_TIMEOUT = 3.0      # give up if no speech starts within this (s)
MAX_UTTERANCE = 20.0     # hard cap on one utterance (s)
MIN_UTTERANCE = 0.3      # ignore blips with less actual speech than this (s)
PRE_ROLL = float(os.environ.get("PRE_ROLL", "0.32"))  # audio kept from just before speech onset (s)

# ── Continued conversation ───────────────────────────────────────────
# Say the wake word once to start; after each reply the mic re-opens for a
# follow-up (no wake word) until you stay quiet for FOLLOWUP_TIMEOUT or say a
# stop phrase. Then it drops back to wake-word-only.
FOLLOWUP_TIMEOUT = float(os.environ.get("FOLLOWUP_TIMEOUT", "8.0"))
FOLLOWUP_CUE = os.environ.get("FOLLOWUP_CUE", "1") not in ("0", "false", "False")
# Barge-in: interrupt the assistant mid-reply by saying the wake word again.
# Wake-word (not loudness) is the trigger so the assistant's own voice on open
# speakers can never false-trigger an interruption.
BARGE_IN_ENABLED = os.environ.get("BARGE_IN_ENABLED", "1") not in ("0", "false", "False")
# Thinking cue: the brain can take many seconds to answer. Play a soft tick the
# moment it starts working (so you know you were heard), repeating gently while
# you wait, so the silence doesn't feel like a hang.
THINKING_CUE = os.environ.get("THINKING_CUE", "1") not in ("0", "false", "False")
THINKING_INTERVAL = float(os.environ.get("THINKING_INTERVAL", "2.0"))  # seconds between ticks
STOP_PHRASES = {
    "never mind", "nevermind", "stop", "stop it", "that's all", "thats all",
    "that is all", "that's it", "thats it", "thanks", "thank you",
    "thanks jarvis", "thank you jarvis", "goodbye", "bye", "cancel", "done",
    "we're done", "were done", "no thanks", "no thank you", "nothing",
}

# ── Speaker verification (ECAPA voice embeddings) ────────────────────
# Only act on the enrolled user's voice — TV dialogue and other people are
# ignored. Enroll once with:  ./voice-venv/bin/python -m voice_assistant.enroll
# Auto-enabled when a profile exists; SPEAKER_VERIFY=0 forces it off.
SPEAKER_VERIFY = os.environ.get("SPEAKER_VERIFY", "auto")
# Cosine gate. Measured margins (kokoro closed-loop test): enrolled voice
# scores ~0.85 vs its profile; other voices 0.04-0.32. 0.40 splits that with
# room on both sides — lower it toward 0.30 if you get falsely rejected.
SPEAKER_THRESHOLD = float(os.environ.get("SPEAKER_THRESHOLD", "0.40"))
# Rejected (non-enrolled) utterances re-open the listen window so the TV can't
# end your conversation — but only this many times before dropping back to idle.
SPEAKER_MAX_REJECTS = int(os.environ.get("SPEAKER_MAX_REJECTS", "3"))
SPEAKER_PROFILE = BASE_DIR / ".speaker_profile.npz"
SPEAKER_MODEL_DIR = BASE_DIR / ".models" / "spkrec-ecapa-voxceleb"
# Windowed matching: the clip is scanned in overlapping windows so the user
# still matches when TV dialogue runs before/after/under their command (a
# whole-clip embedding of mixed voices averages the user away), and the clip
# sent to STT is trimmed to the span of windows that match.
SPEAKER_WINDOW = float(os.environ.get("SPEAKER_WINDOW", "1.6"))  # window length (s)
SPEAKER_HOP = float(os.environ.get("SPEAKER_HOP", "0.8"))        # window stride (s)
# Adaptive profile: confidently-accepted utterances are learned as new voice
# samples, so the profile tracks how the voice varies (morning, tired, sick)
# instead of staying a one-day snapshot. Only windows scoring >=
# SPEAKER_ADAPT_MIN are learned — impostors measured <= 0.33, so poisoning
# needs a voice far closer than the TV. Enrollment anchors are never evicted;
# re-enrolling (without --add) wipes everything learned.
SPEAKER_ADAPT = os.environ.get("SPEAKER_ADAPT", "1") not in ("0", "false", "False")
SPEAKER_ADAPT_MIN = float(os.environ.get("SPEAKER_ADAPT_MIN", "0.55"))
SPEAKER_ADAPT_NOVELTY = float(os.environ.get("SPEAKER_ADAPT_NOVELTY", "0.90"))  # skip near-duplicates
SPEAKER_ADAPT_MAX = int(os.environ.get("SPEAKER_ADAPT_MAX", "16"))  # learned-sample cap

# ── STT (mlx-whisper, Apple Silicon GPU) ─────────────────────────────
# large-v3-turbo: much better real-world accuracy than small (names, noise,
# accents, fast speech), ~0.9s on Apple Silicon — negligible vs brain latency.
# For maximum accuracy try "mlx-community/whisper-large-v3"; for the old fast
# baseline, "mlx-community/whisper-small-mlx".
STT_MODEL = os.environ.get("STT_MODEL", "mlx-community/whisper-large-v3-turbo")
STT_LANGUAGE = "en"
# Confidence gating — drop segments Whisper wasn't confident about instead of
# treating hallucinated text ("Thank you.", "Bye.") as a command. The first
# pair is Whisper's classic no-speech heuristic, slightly tightened; the
# SUSPECT_* pair applies only to known stock hallucination phrases (see
# stt._SUSPECT_PHRASES), so a confidently spoken "thanks" still gets through.
STT_NO_SPEECH_MAX = float(os.environ.get("STT_NO_SPEECH_MAX", "0.5"))
STT_LOGPROB_MIN = float(os.environ.get("STT_LOGPROB_MIN", "-0.7"))
STT_COMPRESSION_MAX = float(os.environ.get("STT_COMPRESSION_MAX", "2.4"))
STT_SUSPECT_NO_SPEECH = float(os.environ.get("STT_SUSPECT_NO_SPEECH", "0.4"))
STT_SUSPECT_LOGPROB = float(os.environ.get("STT_SUSPECT_LOGPROB", "-0.5"))

# ── Media pause ──────────────────────────────────────────────────────
# Pause other audio while a conversation is active (so nothing bleeds into
# speech-to-text), then resume it after. Apple Music / Spotify are paused
# precisely via AppleScript.
PAUSE_ENABLED = os.environ.get("PAUSE_ENABLED", "1") not in ("0", "false", "False")
# PAUSE_SYSTEM: also tap the Play/Pause media key to catch a browser/YouTube tab
# (the only universal lever on macOS 26, which locked down MediaRemote). The key
# is a blind toggle with no play-state read-back, so it ONLY fires when Music and
# Spotify are both closed — otherwise a paused Music session would get resumed
# when you start talking. So this helps browser audio only when no music app is
# open. Set to 0 to disable entirely.
PAUSE_SYSTEM = os.environ.get("PAUSE_SYSTEM", "1") not in ("0", "false", "False")

# ── TTS (Kokoro) ─────────────────────────────────────────────────────
TTS_REPO_ID = "hexgrad/Kokoro-82M"
TTS_VOICE = os.environ.get("TTS_VOICE", "af_heart")
TTS_LANG = os.environ.get("TTS_LANG", "a")  # 'a' = American English
TTS_SPEED = float(os.environ.get("TTS_SPEED", "1.0"))
TTS_SAMPLE_RATE = 24000  # Kokoro output rate

# Fixed reply phrases pre-rendered at startup so they play instantly (no synth
# latency). Must match the exact strings the brain sends: the fast-path intent
# confirmations (app/agent/intent_router.py) plus a few voice/brain phrases.
# Templated replies (volume/brightness with a number) vary and aren't cached.
KNOWN_CONFIRMATIONS = [
    "Paused.", "Resuming.", "Skipping.", "Going back.",
    "Lights on.", "Lights off.", "Turning on the TV.", "TV off.",
    "Muted.", "Unmuted.",
    "Okay.", "Sorry, I couldn't reach the brain.", "Sorry, that didn't work.",
    "Okay, I'm on it — I'll let you know when it's ready.",
    "I'm still working on the last thing — give me a moment.",
]
