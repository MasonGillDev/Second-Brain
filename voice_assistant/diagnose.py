"""Mic + wake-word diagnostic.

Run:  ../voice-venv/bin/python -m voice_assistant.diagnose

Shows the input device, a live mic level meter, and the live wake-word score so
you can tell whether (a) the mic is actually delivering audio, and (b) the wake
model responds when you say the wake word.
"""

import sys
import time

import numpy as np
import sounddevice as sd

from . import config, recorder, vad
from .wake import WakeWordDetector


def main():
    print("=" * 60)
    print("  Voice diagnostic")
    print("=" * 60)

    # 1) Devices
    print("\nDefault input device:")
    try:
        din = sd.query_devices(kind="input")
        print(f"  -> {din['name']}  ({din['max_input_channels']} ch @ {int(din['default_samplerate'])} Hz)")
    except Exception as e:
        print(f"  !! could not query default input: {e}")
    print("\nAll input devices:")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            mark = " (default)" if i == sd.default.device[0] else ""
            print(f"  [{i}] {d['name']}{mark}")

    # 2) Load wake + VAD models
    print()
    detector = WakeWordDetector()
    vad.warm()

    # 3) Live meter
    stream = recorder.open_stream()
    print("\nSpeak now — say the wake word a few times. Ctrl-C to stop.\n")
    print(f"{'mic level':>10} {'bar':<32} {'speech':>7} {'wake score':>10}")

    max_rms = 0.0
    max_score = 0.0
    max_speech = 0.0
    silent_frames = 0
    total_frames = 0
    try:
        t_last = time.time()
        while True:
            frame = recorder.read_frame(stream)
            total_frames += 1
            rms = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))
            score = detector.detect(frame)
            speech = vad.speech_prob(frame)
            max_rms = max(max_rms, rms)
            max_score = max(max_score, score)
            if speech is not None:
                max_speech = max(max_speech, speech)
            if rms < 5:
                silent_frames += 1

            # throttle printing to ~5 Hz
            now = time.time()
            if now - t_last >= 0.2:
                t_last = now
                bars = int(min(rms, 2000) / 2000 * 30)
                meter = "#" * bars
                sp = f"{speech:7.2f}" if speech is not None else "    n/a"
                flag = "  <-- WAKE!" if score >= config.WAKE_THRESHOLD else ""
                sys.stdout.write(f"\r{rms:10.0f} {meter:<32} {sp} {score:10.3f}{flag}      ")
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop()
        stream.close()

    print("\n\n--- summary ---")
    pct_silent = 100 * silent_frames / max(total_frames, 1)
    print(f"  peak mic level : {max_rms:.0f}  (int16 RMS; speech is usually 300-3000)")
    print(f"  peak speech prob: {max_speech:.2f}  (VAD threshold {config.VAD_THRESHOLD})")
    print(f"  peak wake score: {max_score:.3f}  (threshold {config.WAKE_THRESHOLD})")
    print(f"  silent frames  : {pct_silent:.0f}%")
    if max_rms < 5:
        print("\n  ==> Mic is delivering SILENCE. This is a macOS Microphone")
        print("      permission or input-device problem, NOT a wake-word issue.")
        print("      Fix: System Settings > Privacy & Security > Microphone,")
        print("      enable your terminal app (Terminal/iTerm), then relaunch.")
    elif max_score < config.WAKE_THRESHOLD:
        print("\n  ==> Mic works, but the wake word never crossed threshold.")
        print("      Try speaking 'hey jarvis' clearly, or lower the threshold:")
        print("      WAKE_THRESHOLD=0.3 ./voice_assistant/run.sh")
    else:
        print("\n  ==> Mic + wake word both working. The main service should trigger.")


if __name__ == "__main__":
    main()
