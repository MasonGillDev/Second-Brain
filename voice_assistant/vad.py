"""Speech detection via Silero VAD (tiny torch model, in-process).

Replaces the fixed RMS gate for utterance endpointing. Loudness can't tell a
fan or music bed from a voice: steady noise above the gate both false-started
recordings and kept them alive to the MAX_UTTERANCE cap, feeding Whisper pure
noise it then hallucinated commands from. Silero scores *speech* specifically.

Feed the mic's 80 ms frames (1280 samples, int16, 16 kHz) to is_speech();
they're internally re-chunked to the 512-sample windows the model requires.
If the model can't load, is_speech() falls back to the old RMS gate so the
assistant never goes deaf.
"""

import numpy as np

from . import config

_CHUNK = 512  # the only window size silero accepts at 16 kHz

_model = None
_failed = False
_buf = np.zeros(0, dtype=np.float32)
_last_prob = 0.0


def _get_model():
    global _model, _failed
    if _model is None and not _failed:
        try:
            print("  [vad] Loading Silero VAD...")
            from silero_vad import load_silero_vad
            _model = load_silero_vad()
            print("  [vad] Ready.")
        except Exception as e:
            _failed = True
            print(f"  [vad] unavailable ({e}); falling back to RMS gate")
    return _model


def warm() -> None:
    if config.VAD_ENABLED:
        _get_model()


def reset() -> None:
    """Clear the model's recurrent state + chunk buffer between utterances."""
    global _buf, _last_prob
    _buf = np.zeros(0, dtype=np.float32)
    _last_prob = 0.0
    if _model is not None:
        try:
            _model.reset_states()
        except Exception:
            pass


def speech_prob(frame_int16: np.ndarray) -> float | None:
    """Speech probability for this frame (max over the 512-sample chunks it
    completes), or None when the model is unavailable."""
    model = _get_model()
    if model is None:
        return None
    import torch

    global _buf, _last_prob
    _buf = np.concatenate([_buf, frame_int16.astype(np.float32) / 32768.0])
    probs = []
    while _buf.size >= _CHUNK:
        chunk, _buf = _buf[:_CHUNK], _buf[_CHUNK:]
        probs.append(float(model(torch.from_numpy(chunk), config.SAMPLE_RATE).item()))
    if probs:
        _last_prob = max(probs)
    return _last_prob


def _rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(x.astype(np.float32) ** 2)))


def is_speech(frame_int16: np.ndarray) -> bool:
    """True when this mic frame contains speech (VAD), or exceeds the RMS gate
    when the VAD is disabled or unavailable."""
    if config.VAD_ENABLED:
        p = speech_prob(frame_int16)
        if p is not None:
            return p >= config.VAD_THRESHOLD
    return _rms(frame_int16) >= config.SILENCE_RMS
