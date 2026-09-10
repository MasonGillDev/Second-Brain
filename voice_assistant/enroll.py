"""Enroll your voice for speaker verification.

Records a few phrases through the same mic pipeline the assistant uses,
embeds them with the ECAPA model, and saves the profile that
speaker_verify.isolate() checks every utterance against. Run it from a
terminal near the mic you'll actually use:

    ./voice-venv/bin/python -m voice_assistant.enroll          # fresh profile
    ./voice-venv/bin/python -m voice_assistant.enroll --add    # append takes

A voice varies with mood, time of day, and health. If your own commands get
rejected in one of those modes, run --add right then: it appends anchor takes
of the CURRENT voice to the existing profile (and keeps everything the
profile has learned on its own). Plain enrollment overwrites the profile and
wipes learned samples — use it for a fresh start or a new mic position.
"""

import sys

import numpy as np

from . import config, recorder, speaker_verify

PHRASES = [
    "Hey Jarvis, turn on the kitchen lights.",
    "What's on my calendar tomorrow afternoon?",
    "Play some music and set the volume to fifty percent.",
    "Set a timer for twenty five minutes, please.",
    "Never mind, that's all for now, thank you.",
]

MIN_CLIP_SECONDS = 1.5
# Enrollment takes of the SAME voice should agree strongly; below this the
# takes are inconsistent (noise, distance, a different speaker) — redo them.
MIN_CONSISTENCY = 0.40


def main():
    add_mode = "--add" in sys.argv[1:]
    print("=" * 56)
    print(f"  Voice enrollment — {'adding takes to the existing profile' if add_mode else 'fresh profile'}")
    print("=" * 56)

    if add_mode and not speaker_verify.is_enrolled():
        print("No existing profile — doing a fresh enrollment instead.")
        add_mode = False

    if speaker_verify._get_model() is None:
        sys.exit("Could not load the speaker model; see error above.")

    print(f"\nYou'll read {len(PHRASES)} short phrases. Speak naturally, at the")
    print("distance you normally talk to the assistant from.")
    if add_mode:
        print("Use the voice that was being rejected — that's the point of --add.")
    print()

    stream = recorder.open_stream()
    embeddings = []
    try:
        for i, phrase in enumerate(PHRASES, 1):
            print(f'[{i}/{len(PHRASES)}] Say:  "{phrase}"')
            while True:
                print("    listening...")
                audio = recorder.record_utterance(stream, start_timeout=15.0)
                if audio is None:
                    print("    didn't catch any speech — try again")
                    continue
                dur = len(audio) / config.SAMPLE_RATE
                if dur < MIN_CLIP_SECONDS:
                    print(f"    too short ({dur:.1f}s) — say the whole phrase")
                    continue
                emb = speaker_verify.embed(audio)
                if emb is None:
                    sys.exit("Speaker model failed mid-enrollment.")
                embeddings.append(emb)
                print(f"    captured {dur:.1f}s\n")
                break
    finally:
        stream.stop()
        stream.close()

    embs = np.stack(embeddings)
    sims = embs @ embs.T
    off_diag = sims[~np.eye(len(embs), dtype=bool)]
    print(f"Take-to-take consistency: min {off_diag.min():.2f} / mean {off_diag.mean():.2f}")
    if off_diag.min() < MIN_CONSISTENCY:
        print("!! Takes are inconsistent — background noise or varying distance?")
        print("   The profile was saved anyway, but consider re-running in a quiet room.")

    if add_mode:
        profile = speaker_verify._load_profile()
        vs_old = (embs @ profile["all"].T).max(axis=1)
        print(f"New takes vs existing profile: min {vs_old.min():.2f} / max {vs_old.max():.2f}"
              f"  (low = this voice mode was genuinely missing)")
        anchors = np.vstack([profile["anchors"], embs])
        speaker_verify.save_profile(anchors, profile["adapted"])
        print(f"\nAdded {len(embs)} takes: now {len(anchors)} anchors"
              f" + {len(profile['adapted'])} learned samples.")
    else:
        speaker_verify.save_profile(embs)
        print(f"\nProfile saved to {config.SPEAKER_PROFILE}")
    print(f"Verification threshold is {config.SPEAKER_THRESHOLD} (SPEAKER_THRESHOLD to tune;")
    print("lower = more lenient). Restart the voice assistant to activate.")


if __name__ == "__main__":
    main()
