"""Microphone capture helpers built on a single shared sounddevice InputStream.

The stream stays open for the life of the process; the wake loop reads frames
from it continuously, and record_utterance() drains it with VAD-based
endpointing once the wake word fires.
"""

from collections import deque

import numpy as np
import sounddevice as sd

from . import config, vad


def open_stream() -> sd.InputStream:
    stream = sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        channels=config.CHANNELS,
        dtype="int16",
        blocksize=config.FRAME_SAMPLES,
    )
    stream.start()
    return stream


def read_frame(stream: sd.InputStream) -> np.ndarray:
    """Read one mono int16 frame (FRAME_SAMPLES long)."""
    block, _ = stream.read(config.FRAME_SAMPLES)
    return np.ascontiguousarray(block[:, 0])


def drain(stream: sd.InputStream) -> None:
    """Discard any buffered audio (e.g. the assistant's own voice during TTS)."""
    avail = stream.read_available
    if avail > 0:
        stream.read(avail)


def record_utterance(stream: sd.InputStream, start_timeout: float | None = None) -> np.ndarray | None:
    """Record from the running stream until trailing silence.

    Endpointing is speech-based (Silero VAD), not loudness-based: steady
    background noise (fan, AC, music bed) neither starts a phantom recording
    nor keeps one alive to the MAX_UTTERANCE cap. A short PRE_ROLL of audio
    from just before speech onset is prepended so leading consonants the gate
    missed aren't clipped.

    start_timeout: how long to wait for speech to *begin* before giving up
    (defaults to config.START_TIMEOUT; pass config.FOLLOWUP_TIMEOUT for the
    wake-free follow-up window). Returns a mono int16 array, or None if no
    speech was detected.
    """
    if start_timeout is None:
        start_timeout = config.START_TIMEOUT
    frame_dur = config.FRAME_SAMPLES / config.SAMPLE_RATE
    max_frames = int(config.MAX_UTTERANCE / frame_dur)
    # Adaptive endpointing: short utterances (commands) end after a quick pause;
    # long ones (dictation) get the patient SILENCE_DURATION so thinking pauses
    # don't clip. The required trailing silence is chosen per-frame below based
    # on how much *speech* has accumulated so far.
    quick_limit = int(config.SILENCE_QUICK / frame_dur)
    long_limit = int(config.SILENCE_DURATION / frame_dur)
    cutoff_frames = int(config.ADAPTIVE_SPEECH_CUTOFF / frame_dur)
    start_limit = int(start_timeout / frame_dur)

    vad.reset()
    frames: list[np.ndarray] = []
    preroll: deque = deque(maxlen=max(1, int(config.PRE_ROLL / frame_dur)))
    silence_run = 0
    speech_frames = 0
    started = False

    for i in range(max_frames):
        samples = read_frame(stream)
        speech = vad.is_speech(samples)

        if speech:
            if not started:
                frames.extend(preroll)  # keep the onset the gate hadn't opened for
                preroll.clear()
            started = True
            speech_frames += 1
            silence_run = 0
            frames.append(samples)
        elif started:
            silence_run += 1
            frames.append(samples)
            # Short command so far → end on a quick pause; long utterance →
            # tolerate a longer pause (thinking mid-dictation).
            required = long_limit if speech_frames >= cutoff_frames else quick_limit
            if silence_run >= required:
                break
        else:
            preroll.append(samples)
            if i >= start_limit:
                return None  # nobody spoke

    if not started or not frames:
        return None

    # Gate on actual *speech* time, not clip length — the clip also contains
    # the pre-roll and trailing silence, which would let any blip through.
    if speech_frames * frame_dur < config.MIN_UTTERANCE:
        return None
    return np.concatenate(frames)
