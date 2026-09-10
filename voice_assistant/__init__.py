"""
Second Brain — standalone voice assistant service.

Runs in its own Python 3.12 venv (../voice-venv), fully decoupled from the
dashboard. Pipeline:

    wake word -> record -> STT -> dashboard /api/inference -> TTS -> playback

The dashboard only ever sees text in / text out. All audio (mic, speech-to-text,
text-to-speech, playback) lives here.

Run with:
    ../voice-venv/bin/python -m voice_assistant
"""
