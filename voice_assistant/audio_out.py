"""Single persistent audio-output stream for all playback (speech + cues).

Opening a fresh OutputStream per sound (sd.play) is what broke playback on
macOS: cue tones at 16 kHz alternating with speech at 24 kHz forced the
CoreAudio output unit to reconfigure over and over (AUHAL -10851 'Invalid
Property Value' warnings) until it wedged and refused new streams
(PaErrorCode -9986) — replies were silently lost. Everything now writes
float32 mono at OUT_RATE to one long-lived stream.

Never raises: on a device error (e.g. the default output moved to AirPods)
the stream is rebuilt once; if that fails too, the sound is dropped and the
assistant carries on.
"""

import numpy as np
import sounddevice as sd

from . import config

OUT_RATE = config.TTS_SAMPLE_RATE  # one fixed rate for everything played
_CHUNK = 1024  # ~43 ms per write — the stop-poll granularity for barge-in

_stream: "sd.OutputStream | None" = None


def warm() -> None:
    try:
        _get_stream()
    except Exception as e:
        print(f"  [audio] output stream unavailable at warm-up ({e})")


def reset() -> None:
    """Tear down the stream; the next play() rebuilds it."""
    global _stream
    if _stream is not None:
        try:
            _stream.close()
        except Exception:
            pass
        _stream = None


def _get_stream() -> sd.OutputStream:
    global _stream
    if _stream is not None and _stream.active:
        return _stream
    reset()
    _stream = sd.OutputStream(samplerate=OUT_RATE, channels=1, dtype="float32")
    _stream.start()
    return _stream


def play(audio: np.ndarray, should_stop=None) -> bool:
    """Play mono float32 audio at OUT_RATE through the persistent stream.

    Polls should_stop between ~43 ms writes; returns True if playback was
    aborted early. Never raises — device errors rebuild the stream once,
    then drop the sound.
    """
    audio = np.ascontiguousarray(np.asarray(audio, dtype=np.float32))
    if audio.size == 0:
        return False

    for attempt in (0, 1):
        try:
            stream = _get_stream()
            i = 0
            while i < len(audio):
                if should_stop is not None and should_stop():
                    stream.abort()  # flush what's buffered
                    stream.start()  # stream stays usable for the next sound
                    return True
                try:
                    stream.write(audio[i:i + _CHUNK])
                except sd.PortAudioError as e:
                    # A gap between chunks (synthesis slower than playback)
                    # underflows the stream; the data still played — benign.
                    if "underflow" not in str(e).lower():
                        raise
                i += _CHUNK
            return False
        except Exception as e:
            print(f"  [audio] output error ({e}); "
                  f"{'rebuilding stream' if attempt == 0 else 'dropping audio'}")
            reset()
    return False
