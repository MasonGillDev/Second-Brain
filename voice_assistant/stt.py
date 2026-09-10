"""Speech-to-text via mlx-whisper (in-process, Apple Silicon GPU).

The model loads on first use and stays resident. transcribe() accepts a raw
mono numpy array (int16 or float32) at 16 kHz — no temp files.

Output is confidence-gated: Whisper hallucinates plausible stock text
("Thank you.", "Bye.") from noise or breath, and several of those collide with
the assistant's stop phrases — so segments the decoder wasn't confident about
are dropped instead of becoming phantom commands.
"""

import re
import time

import numpy as np
import mlx_whisper

from . import config

_warmed = False

# Stock phrases Whisper invents from noise/silence (YouTube-outro artifacts in
# its training data). A segment matching one is kept only when the decoder was
# confident — a real spoken "thanks" scores well; a hallucinated one rides on
# noise and scores poorly.
_SUSPECT_PHRASES = {
    "thank you", "thanks", "thank you for watching", "thanks for watching",
    "thank you so much for watching", "thank you very much", "subscribe",
    "please subscribe", "bye", "you", "so", "yeah", "okay", "uh", "um", "oh",
}


def warm() -> None:
    """Force the model to load by transcribing a second of silence."""
    global _warmed
    if _warmed:
        return
    print("  [stt] Loading Whisper model...")
    t0 = time.time()
    mlx_whisper.transcribe(
        np.zeros(config.SAMPLE_RATE, dtype=np.float32),
        path_or_hf_repo=config.STT_MODEL,
        language=config.STT_LANGUAGE,
    )
    _warmed = True
    print(f"  [stt] Ready in {time.time() - t0:.1f}s")


def _gate_segments(segments: list[dict]) -> str:
    """Join segment texts, dropping the ones that look hallucinated."""
    kept = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        no_speech = float(seg.get("no_speech_prob", 0.0))
        logprob = float(seg.get("avg_logprob", 0.0))
        ratio = float(seg.get("compression_ratio", 1.0))

        if no_speech > config.STT_NO_SPEECH_MAX and logprob < config.STT_LOGPROB_MIN:
            print(f"  [stt] dropped no-speech segment ({no_speech=:.2f}, {logprob=:.2f}): {text!r}")
            continue
        if ratio > config.STT_COMPRESSION_MAX:
            print(f"  [stt] dropped repetition loop ({ratio=:.2f}): {text!r}")
            continue
        norm = re.sub(r"[^a-z ]", "", text.lower()).strip()
        if norm in _SUSPECT_PHRASES and (
            logprob < config.STT_SUSPECT_LOGPROB or no_speech > config.STT_SUSPECT_NO_SPEECH
        ):
            print(f"  [stt] dropped likely hallucination ({no_speech=:.2f}, {logprob=:.2f}): {text!r}")
            continue
        kept.append(text)
    return " ".join(kept).strip()


def transcribe(audio: np.ndarray) -> str:
    """Transcribe mono 16 kHz audio (int16 or float32) to text."""
    warm()
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    else:
        audio = audio.astype(np.float32)

    t0 = time.time()
    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=config.STT_MODEL,
        language=config.STT_LANGUAGE,
        # Feeding the previous window's text back in is where looping
        # hallucinations come from; utterances here are single short commands.
        condition_on_previous_text=False,
    )
    text = _gate_segments(result.get("segments", []))
    print(f"  [stt] {time.time() - t0:.2f}s -> {text!r}")
    return text
