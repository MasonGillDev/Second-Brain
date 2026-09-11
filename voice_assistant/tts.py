"""Text-to-speech via Kokoro (in-process) with streaming playback.

Kokoro yields audio chunk-by-chunk; we play each chunk as it arrives so speech
starts within ~1s instead of waiting for the whole utterance to synthesize.
All playback (speech and cue tones) goes through audio_out's single persistent
stream — per-sound sd.play() streams wedged CoreAudio (see audio_out.py).
"""

import time

import numpy as np

from . import audio_out, config
from .speech_text import normalize

_pipeline = None
# Pre-rendered audio for a small set of fixed confirmation phrases ("Paused.",
# "TV off.", ...) so command replies play instantly instead of paying ~0.4s of
# kokoro synth every time. Keyed by the exact reply string.
_phrase_cache: dict[str, np.ndarray] = {}


def prewarm(phrases) -> None:
    """Pre-render fixed confirmation phrases into the cache (call once at startup)."""
    _get_pipeline()
    t0 = time.time()
    n = 0
    for p in phrases:
        p = (p or "").strip()
        if p and p not in _phrase_cache:
            _phrase_cache[p] = synth(p)
            n += 1
    if n:
        print(f"  [tts] pre-rendered {n} confirmation phrases in {time.time() - t0:.1f}s")


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        print("  [tts] Loading Kokoro model...")
        t0 = time.time()
        from kokoro import KPipeline  # imported lazily — heavy (torch)
        _pipeline = KPipeline(lang_code=config.TTS_LANG, repo_id=config.TTS_REPO_ID)
        print(f"  [tts] Ready in {time.time() - t0:.1f}s")
    return _pipeline


def warm() -> None:
    _get_pipeline()


def synth(text: str) -> np.ndarray:
    """Synthesize text to a single float32 mono array at TTS_SAMPLE_RATE.

    Useful for tests / non-realtime callers. speak() is preferred for live use.
    """
    text = normalize(text)
    pipeline = _get_pipeline()
    chunks = []
    for _, _, audio in pipeline(text, voice=config.TTS_VOICE, speed=config.TTS_SPEED):
        chunks.append(_to_numpy(audio))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks)


def speak(text: str) -> None:
    """Synthesize and play text, streaming chunk-by-chunk."""
    text = normalize((text or "").strip())
    if not text:
        return
    cached = _phrase_cache.get(text)
    if cached is not None:
        audio_out.play(cached)
        return
    pipeline = _get_pipeline()
    t0 = time.time()
    first = True
    for _, _, audio in pipeline(text, voice=config.TTS_VOICE, speed=config.TTS_SPEED):
        chunk = _to_numpy(audio)
        if first:
            print(f"  [tts] first audio in {time.time() - t0:.2f}s")
            first = False
        audio_out.play(chunk)


def speak_streaming(text: str, should_stop) -> bool:
    """Synthesize and play, but abort early if should_stop() returns True.

    Returns True if playback was aborted before finishing (i.e. interrupted).
    should_stop is polled between chunks and ~every 43ms during playback, so a
    barge-in stops the assistant mid-sentence.
    """
    text = normalize((text or "").strip())
    if not text:
        return False
    cached = _phrase_cache.get(text)
    if cached is not None:
        return audio_out.play(cached, should_stop)
    pipeline = _get_pipeline()
    for _, _, audio in pipeline(text, voice=config.TTS_VOICE, speed=config.TTS_SPEED):
        if should_stop():
            return True
        if audio_out.play(_to_numpy(audio), should_stop):
            return True
    return False


def play_earcon() -> None:
    """Bright beep to signal 'listening' right after the wake word."""
    _play_tone(880.0, 0.12, 0.18)


def play_listen_cue() -> None:
    """Soft, short tick to signal the follow-up mic is open (continued convo)."""
    _play_tone(660.0, 0.07, 0.07)


def play_thinking_tick() -> None:
    """Very soft low tick while the brain is processing, so a long wait isn't dead air."""
    _play_tone(330.0, 0.09, 0.05)


def _play_tone(freq: float, dur: float, amp: float) -> None:
    """Play a short sine with fades so it doesn't click. Never raises.

    Generated at the shared output rate — cue tones at a different rate than
    speech are exactly what wedged the CoreAudio output unit.
    """
    try:
        n = int(audio_out.OUT_RATE * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        tone = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        fade = min(256, n // 4)
        if fade > 0:
            env = np.ones(n, dtype=np.float32)
            env[:fade] = np.linspace(0, 1, fade)
            env[-fade:] = np.linspace(1, 0, fade)
            tone *= env
        audio_out.play(tone)
    except Exception:
        pass  # cues are cosmetic; never let them break the pipeline


def _to_numpy(audio) -> np.ndarray:
    """Kokoro yields a torch.Tensor; normalize to a contiguous float32 array."""
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    return np.ascontiguousarray(np.asarray(audio, dtype=np.float32))
