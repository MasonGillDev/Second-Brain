"""Speaker verification — only act on the enrolled user's voice.

TV dialogue is real speech, so the VAD and Whisper both (correctly) let it
through; this is the layer that tells *whose* speech it is, using ECAPA-TDNN
embeddings (speechbrain, local CPU) against the profile saved by enroll.py.

Matching is WINDOWED, not whole-clip: when the TV keeps talking, endpointing
holds the recording open past the user's command, and a whole-clip embedding
of the mixed voices averages the user away (real failure: user + TV scored
0.28 and got rejected). isolate() scans overlapping windows, accepts if any
window matches the profile, and returns the clip trimmed to the span where
the user actually spoke — so trailing TV dialogue never reaches Whisper.
Measured cost: ~30ms on a normal command, ~220ms at the 20s utterance cap.

The profile ADAPTS: a voice changes with mood, time of day, and health, so a
one-day enrollment snapshot slowly starts falsely rejecting its own owner.
Confidently-accepted utterances (>= SPEAKER_ADAPT_MIN, far above any measured
impostor score) are learned as extra voice samples, capped and deduplicated,
so coverage of the user's voice range grows with use. Enrollment takes are
anchors and are never evicted; `enroll --add` appends anchors for a voice
mode that's being rejected right now.

Fail-open by design: no profile, model failure, or SPEAKER_VERIFY=0 all mean
"accept everyone" — verification can restrict the assistant, never brick it.

Enroll (one-time, from a terminal near the mic you actually use):
    ./voice-venv/bin/python -m voice_assistant.enroll
"""

import os

import numpy as np

from . import config

# Trim span = contiguous windows around the best-matching one. A window stays
# in the span while its score clears BOTH floors: near the accept threshold
# (absolute) and near the best window (relative). The user's edge windows are
# partially TV-overlapped and score lower — hence the margins — while pure-TV
# windows fall below and cut the span. Window overlap (hop < window) already
# pads the kept audio, so dropping an edge window doesn't clip words.
_TRIM_MARGIN = 0.15    # absolute: keep windows >= SPEAKER_THRESHOLD - this
_TRIM_RELATIVE = 0.30  # relative: keep windows >= best - this
# encode_batch falls off a CPU fast path above ~12 windows (110ms -> 7-10s
# measured on this machine), so windows are embedded in small sub-batches.
_BATCH = 8

_model = None
_failed = False
# {"anchors": (n, d), "adapted": (m, d), "all": (n+m, d), "mean": (d,)} — all rows L2-normalized
_profile = None


def enabled() -> bool:
    """Verification is on when a profile exists, unless explicitly disabled."""
    if config.SPEAKER_VERIFY in ("0", "false", "False"):
        return False
    return is_enrolled()


def is_enrolled() -> bool:
    return config.SPEAKER_PROFILE.exists()


def warm() -> None:
    if enabled():
        _get_model()
        _load_profile()


def _get_model():
    global _model, _failed
    if _model is None and not _failed:
        try:
            print("  [speaker] Loading ECAPA voice model...")
            from speechbrain.inference.speaker import EncoderClassifier
            _model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=str(config.SPEAKER_MODEL_DIR),
            )
            print("  [speaker] Ready.")
        except Exception as e:
            _failed = True
            print(f"  [speaker] unavailable ({e}); accepting all voices")
    return _model


def _normalize(rows: np.ndarray) -> np.ndarray:
    return rows / (np.linalg.norm(rows, axis=1, keepdims=True) + 1e-9)


def _load_profile():
    global _profile
    if _profile is None and config.SPEAKER_PROFILE.exists():
        try:
            data = np.load(config.SPEAKER_PROFILE)
            anchors = _normalize(data["embeddings"])
            adapted = data["adapted"] if "adapted" in data else np.zeros((0, anchors.shape[1]))
            adapted = _normalize(adapted) if len(adapted) else adapted
            _profile = _build_profile(anchors, adapted)
        except Exception as e:
            print(f"  [speaker] bad profile ({e}); accepting all voices")
    return _profile


def _build_profile(anchors: np.ndarray, adapted: np.ndarray) -> dict:
    all_embs = np.vstack([anchors, adapted]) if len(adapted) else anchors
    mean = all_embs.mean(axis=0)
    mean /= np.linalg.norm(mean) + 1e-9
    return {"anchors": anchors, "adapted": adapted, "all": all_embs, "mean": mean}


def save_profile(anchors: np.ndarray, adapted: np.ndarray | None = None) -> None:
    """Persist the profile atomically and refresh the in-memory copy. The file
    format is owned here — enroll.py and adaptation both write through this."""
    global _profile
    anchors = _normalize(np.asarray(anchors))
    adapted = (_normalize(np.asarray(adapted))
               if adapted is not None and len(adapted) else np.zeros((0, anchors.shape[1])))
    tmp = config.SPEAKER_PROFILE.with_suffix(".tmp.npz")
    np.savez(tmp, embeddings=anchors, adapted=adapted)
    os.replace(tmp, config.SPEAKER_PROFILE)
    _profile = _build_profile(anchors, adapted)


def _maybe_adapt(emb: np.ndarray, sim: float) -> None:
    """Learn a confidently-accepted utterance as a new voice sample.

    Guards: high similarity (impostors measured <= 0.33, so >= ADAPT_MIN can
    only be the user), novelty (near-duplicates of known samples add nothing),
    and a cap — the most redundant learned sample is evicted, never an anchor.
    """
    if not config.SPEAKER_ADAPT or sim < config.SPEAKER_ADAPT_MIN:
        return
    profile = _profile
    if profile is None:
        return
    closest = float(np.max(profile["all"] @ emb))
    if closest >= config.SPEAKER_ADAPT_NOVELTY:
        return  # this voice mode is already well covered
    adapted = np.vstack([profile["adapted"], emb]) if len(profile["adapted"]) else emb[np.newaxis, :]
    if len(adapted) > config.SPEAKER_ADAPT_MAX:
        sims = adapted @ adapted.T
        np.fill_diagonal(sims, -1.0)
        adapted = np.delete(adapted, int(np.argmax(sims.max(axis=1))), axis=0)
    try:
        save_profile(profile["anchors"], adapted)
        print(f"  [speaker] learned a new voice sample (sim {sim:.2f}, {len(adapted)} learned)")
    except Exception as e:
        print(f"  [speaker] could not save learned sample ({e})")


def embed(audio_int16: np.ndarray) -> np.ndarray | None:
    """L2-normalized ECAPA embedding of a mono 16 kHz clip, or None if the
    model is unavailable. Used by enroll.py."""
    model = _get_model()
    if model is None:
        return None
    import torch

    wav = torch.from_numpy(audio_int16.astype(np.float32) / 32768.0).unsqueeze(0)
    with torch.no_grad():
        emb = model.encode_batch(wav).squeeze().cpu().numpy()
    return emb / (np.linalg.norm(emb) + 1e-9)


def _embed_windows(windows: np.ndarray) -> np.ndarray:
    """Embed a (n, samples) int16 batch -> (n, dim) row-normalized, in
    sub-batches to stay on the fast CPU path."""
    import torch

    model = _get_model()
    wav = torch.from_numpy(windows.astype(np.float32) / 32768.0)
    parts = []
    with torch.no_grad():
        for i in range(0, len(wav), _BATCH):
            parts.append(model.encode_batch(wav[i:i + _BATCH]).squeeze(1).cpu().numpy())
    embs = np.concatenate(parts)
    return embs / (np.linalg.norm(embs, axis=1, keepdims=True) + 1e-9)


def _similarities(embs: np.ndarray, profile: dict) -> np.ndarray:
    """Per-row cosine vs the profile: best of (vs mean, vs closest sample)."""
    return np.maximum(embs @ profile["mean"], (embs @ profile["all"].T).max(axis=1))


def isolate(audio_int16: np.ndarray) -> tuple[np.ndarray | None, float]:
    """Find the enrolled speaker inside a clip.

    Returns (clip trimmed to the user's span, best window similarity), or
    (None, best_sim) when no window matches the profile. Fail-open: the
    original clip with sim 1.0 when verification is off or unavailable.
    """
    if not enabled():
        return audio_int16, 1.0
    profile = _load_profile()
    if profile is None or _get_model() is None:
        return audio_int16, 1.0

    sr = config.SAMPLE_RATE
    win = int(config.SPEAKER_WINDOW * sr)
    hop = int(config.SPEAKER_HOP * sr)
    n = len(audio_int16)

    # Short clip: one decision, nothing to trim.
    if n <= win + hop:
        embs = _embed_windows(audio_int16[np.newaxis, :])
        best = float(_similarities(embs, profile)[0])
        if best < config.SPEAKER_THRESHOLD:
            return None, best
        _maybe_adapt(embs[0], best)
        return audio_int16, best

    starts = list(range(0, n - win + 1, hop))
    if starts[-1] + win < n:
        starts.append(n - win)  # cover the tail
    windows = np.stack([audio_int16[s:s + win] for s in starts])
    embs = _embed_windows(windows)
    sims = _similarities(embs, profile)

    b = int(np.argmax(sims))
    best = float(sims[b])
    if best < config.SPEAKER_THRESHOLD:
        return None, best

    # Expand a contiguous span around the best window; a window below the
    # floor is someone else (or silence) and cuts the span there.
    floor = max(config.SPEAKER_THRESHOLD - _TRIM_MARGIN, best - _TRIM_RELATIVE)
    i = j = b
    while i > 0 and sims[i - 1] >= floor:
        i -= 1
    while j < len(sims) - 1 and sims[j + 1] >= floor:
        j += 1
    span = audio_int16[starts[i]:min(n, starts[j] + win)]

    # Learn from the whole trimmed span, not the best window: anchors are
    # whole-utterance embeddings, and a 1.6s window embedding is too noisy to
    # transfer to other phrases in the same voice mode. BUT only in clean
    # conditions: if anything outside the span has speech-level energy,
    # another voice was in the room, and its bleed under the user's speech
    # poisons the profile (verified: learning a TV-mixed span raised the TV's
    # own score past the threshold). Adaptation just waits for a quiet turn.
    if config.SPEAKER_ADAPT:
        outside = [w for k, w in enumerate(windows) if k < i or k > j]
        quiet = all(
            float(np.sqrt(np.mean(w.astype(np.float32) ** 2))) < config.SILENCE_RMS
            for w in outside
        )
        if quiet:
            span_emb = embed(span)
            if span_emb is not None:
                _maybe_adapt(span_emb, float(_similarities(span_emb[np.newaxis, :], profile)[0]))
    return span, best
