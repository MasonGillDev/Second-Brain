# Voice Assistant

A standalone, fully local voice interface for the Second Brain. It is **decoupled**
from the dashboard — the dashboard only ever exchanges *text* with it.

```
wake word ─▶ [ record ─▶ STT ─▶ POST /api/inference ─▶ TTS ─▶ follow-up ]*
(openWakeWord)(mic+VAD)(whisper)  (dashboard = brain)   (kokoro)   window
└────────────────────── all audio stays in this process ──────────────────┘
```

**Continued conversation:** say the wake word *once* to start. After each reply
the mic re-opens for a follow-up (~8s, no wake word needed) so you can keep
talking naturally. The conversation ends when you stay quiet past the follow-up
window or say a stop phrase ("never mind", "stop", "that's all", "thanks",
"goodbye", ...), then it drops back to wake-word-only. Context carries across
turns because the dashboard keeps one shared conversation.

**Barge-in:** say the wake word again while the assistant is speaking to cut it
off and give a new command. The wake word (not loudness) is the trigger, so the
assistant's own voice through open speakers can never false-trigger it.

**Speaker verification:** enroll your voice once and the assistant only acts on
*you* — TV dialogue, guests, and other voices are silently ignored (they score
low against your ECAPA voice profile and never reach the brain). Enroll with
`./voice-venv/bin/python -m voice_assistant.enroll` (reads 5 short phrases);
auto-enabled once the profile exists, `SPEAKER_VERIFY=0` to force off. A
rejected voice re-opens the listen window (so the TV can't end your
conversation), capped at `SPEAKER_MAX_REJECTS` before dropping back to idle.
Matching is windowed, so speaking *over* a running TV still works: the clip is
scanned in overlapping ~1.6s windows, you match if any window is you, and the
audio sent to STT is trimmed to your span — TV dialogue before/after your
command is cut instead of polluting the transcript. Costs ~30ms per normal
command (~220ms worst case at the 20s cap).

The profile **adapts to voice drift** (mood, morning voice, being sick):
confidently-accepted utterances (sim >= `SPEAKER_ADAPT_MIN`, far above any
impostor score) are learned as extra voice samples — capped, deduplicated,
and never displacing your enrollment takes. Modes even chain: learning a
slightly-off voice pulls further-off voices into range. If a voice mode is
being rejected *right now* (watch for the "close miss" hint in the logs), run
`enroll --add` in that voice — it appends anchors to the existing profile
instead of overwriting it.

**Pause other audio:** while a conversation is active, other audio is paused so
nothing bleeds into speech-to-text, then resumed when it ends. Apple Music and
Spotify are paused precisely via AppleScript (only what was actually playing is
resumed). `PAUSE_SYSTEM` additionally taps the Play/Pause media key to catch a
browser/YouTube tab — the only universal lever on macOS 26 (which locked down
MediaRemote). Because that key is a blind toggle, it only fires when Music and
Spotify are both closed (otherwise it could resume a paused music session), so
it helps browser audio only when no music app is open.

## Why its own venv

`kokoro` requires Python `>=3.10,<3.13`, but the dashboard runs on Python 3.14.
So this service lives in its own interpreter (`../voice-venv`, Python 3.12) and
talks to the dashboard purely over HTTP text. The two never share a process.

## Setup (already done once)

```bash
# from repo root
brew install python@3.12 espeak-ng
/opt/homebrew/bin/python3.12 -m venv voice-venv
./voice-venv/bin/pip install -r voice_assistant/requirements.txt
```

Models (Whisper, Kokoro-82M, openWakeWord) download automatically on first run
and are cached after that.

The dashboard auth token is read from the macOS Keychain service `voice-api-key`
(the same one the dashboard's `/api/inference` checks).

## Run

```bash
# from repo root — the dashboard must be running on :5001
./voice-venv/bin/python -m voice_assistant
# or:
./voice_assistant/run.sh
```

First launch asks for **Microphone** permission (macOS). Say the wake word
(default **"hey jarvis"**), wait for the beep, then speak. The reply is spoken back.

## Configuration

All via environment variables (see `config.py`):

| Var | Default | Notes |
|-----|---------|-------|
| `WAKE_WORD` | `hey_jarvis` | also: `alexa`, `hey_mycroft`, `hey_rhasspy` |
| `WAKE_THRESHOLD` | `0.5` | raise to reduce false triggers |
| `TTS_VOICE` | `af_heart` | any Kokoro voice |
| `TTS_SPEED` | `1.0` | |
| `STT_MODEL` | `mlx-community/whisper-large-v3-turbo` | `...whisper-large-v3` for max accuracy; `...whisper-small-mlx` for the fast baseline |
| `BRAIN_URL` | `http://127.0.0.1:5001` | dashboard base URL |
| `SPEAKER_VERIFY` | `auto` | on when a voice profile exists; `0` = accept anyone |
| `SPEAKER_THRESHOLD` | `0.40` | cosine similarity gate vs the enrolled profile (lower if falsely rejected) |
| `SPEAKER_MAX_REJECTS` | `3` | rejected voices re-open the mic this many times, then idle |
| `SPEAKER_ADAPT` | `1` | learn confidently-accepted utterances as voice samples (`0` to freeze) |
| `SPEAKER_ADAPT_MIN` | `0.55` | minimum sim to learn from an utterance |
| `SPEAKER_ADAPT_MAX` | `16` | cap on learned samples (most redundant evicted first) |
| `VAD_ENABLED` | `1` | Silero VAD speech gate for end-pointing (`0` = raw RMS gate) |
| `VAD_THRESHOLD` | `0.5` | speech probability needed to count a frame as speech |
| `PRE_ROLL` | `0.32` | seconds of audio kept from just before speech onset |
| `SILENCE_RMS` | `450` | fallback end-pointing gate (only if the VAD can't load) |
| `SILENCE_QUICK` | `0.7` | pause (s) that ends a *short* utterance (command) — snappy |
| `ADAPTIVE_SPEECH_CUTOFF` | `2.0` | once you've spoken this long, switch to the patient pause |
| `SILENCE_DURATION` | `2.0` | patient pause (s) for long utterances — room to think mid-sentence |
| `FOLLOWUP_TIMEOUT` | `8.0` | seconds to wait for a wake-free follow-up |
| `FOLLOWUP_CUE` | `1` | soft tick when the follow-up mic opens (`0` to silence) |
| `BARGE_IN_ENABLED` | `1` | say the wake word to interrupt the assistant mid-reply (`0` to disable) |
| `THINKING_CUE` | `1` | soft tick while the brain is working so the wait isn't dead air (`0` to disable) |
| `THINKING_INTERVAL` | `2.0` | seconds between thinking ticks |
| `PAUSE_ENABLED` | `1` | pause Music/Spotify during a conversation (`0` to disable) |
| `PAUSE_SYSTEM` | `1` | also tap the media key to pause a browser/YouTube tab (`0` to disable) |

## Layout

- `wake.py` — openWakeWord detector
- `vad.py` — Silero VAD speech gate (endpointing on *speech*, not loudness)
- `speaker_verify.py` — ECAPA voice verification (only act on the enrolled voice)
- `enroll.py` — one-time voice enrollment CLI
- `recorder.py` — shared mic stream + VAD utterance capture with pre-roll
- `stt.py` — mlx-whisper transcription with hallucination/confidence gating (in-process)
- `tts.py` — Kokoro synthesis + streaming playback (in-process)
- `audio_out.py` — the single persistent output stream everything plays through
- `brain_client.py` — POST text to the dashboard, get text back
- `main.py` — the orchestration loop
