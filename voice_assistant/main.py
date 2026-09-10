"""Voice assistant orchestrator.

Continued-conversation flow:
    wake word ─▶ [ turn: record ─▶ STT ─▶ brain ─▶ TTS ─▶ follow-up window ]*
The wake word only starts a conversation; follow-ups need no wake word until
you go quiet (FOLLOWUP_TIMEOUT) or say a stop phrase. Saying the wake word again
while the assistant is talking interrupts it (barge-in).
"""

import queue
import re
import threading

from . import audio_out, brain_client, callback_server, config, playback, recorder, speaker_verify, stt, tts, vad
from .wake import WakeWordDetector


def _normalize(text: str) -> str:
    """Lowercase and strip to letters/spaces for stop-phrase matching."""
    return re.sub(r"[^a-z ]", "", text.lower()).strip()


def _is_stop_phrase(text: str) -> bool:
    """True only when the whole utterance is essentially a stop phrase.

    Matching the full normalized utterance (not a substring) means 'stop the
    timer' won't end the conversation, but a bare 'stop' will.
    """
    return _normalize(text) in config.STOP_PHRASES


def _ask_with_thinking(text: str) -> tuple[str, str, bool, dict | None]:
    """Call the brain while playing a soft 'thinking' tick so the wait (the brain
    can take many seconds) doesn't feel like a hang. Re-raises any brain error.
    Returns (reply_text, status, music_touched, thread) — see brain_client.ask.

    First tick is immediate ('heard you, working on it'); it then repeats every
    THINKING_INTERVAL seconds until the response arrives.
    """
    if not config.THINKING_CUE:
        return brain_client.ask(text)

    result: dict = {}

    def _call():
        try:
            result["value"] = brain_client.ask(text)
        except Exception as e:
            result["error"] = e

    worker = threading.Thread(target=_call, daemon=True)
    worker.start()
    tts.play_thinking_tick()  # immediate acknowledgement
    while True:
        worker.join(timeout=config.THINKING_INTERVAL)
        if not worker.is_alive():
            break
        tts.play_thinking_tick()

    if "error" in result:
        raise result["error"]
    return result.get("value", ("", "complete", False, None))


def _deliver_pending(stream, detector) -> None:
    """Speak any results the brain pushed back from a backgrounded task (slow
    work that ran async). Called only at idle, so we never talk over a live turn.
    Plays the earcon first as a proactive-speech cue, pauses other audio while
    speaking, then drains the mic echo so the assistant's own voice can't false-trigger."""
    spoke = False
    music_touched = False
    while True:
        try:
            item = callback_server.announcements.get_nowait()
        except queue.Empty:
            break
        text = item.get("text", "")
        music_touched = music_touched or item.get("music_touched", False)
        if not text.strip():
            continue
        if not spoke:
            playback.pause()
            spoke = True
        tts.play_earcon()
        print(f"  Brain (async): {text}")
        tts.speak(text)
    if spoke:
        if music_touched:
            playback.release_claims()
        playback.resume()
        recorder.drain(stream)
        detector.reset()


def _speak(text: str, stream, detector) -> bool:
    """Speak a reply. If barge-in is on, listen for the wake word during playback
    and stop early when heard. Returns True if interrupted by the wake word.

    Wake-word (not loudness) is the trigger, so the assistant's own voice coming
    back through open speakers can't false-trigger an interruption.
    """
    if not config.BARGE_IN_ENABLED:
        tts.speak(text)
        return False

    stop_event = threading.Event()
    player = threading.Thread(
        target=tts.speak_streaming, args=(text, stop_event.is_set), daemon=True
    )
    detector.reset()
    player.start()

    interrupted = False
    while player.is_alive():
        if detector.triggered(recorder.read_frame(stream)):
            interrupted = True
            stop_event.set()
            break
    player.join(timeout=3)
    detector.reset()
    return interrupted


def run() -> None:
    print("=" * 56)
    print("  Second Brain — Voice Assistant")
    print(f"  Wake word : {config.WAKE_WORD!r}  (threshold {config.WAKE_THRESHOLD})")
    print(f"  Brain     : {config.DASHBOARD_URL}{config.INFERENCE_PATH}")
    print(f"  Voice     : {config.TTS_VOICE}  |  follow-up {config.FOLLOWUP_TIMEOUT:.0f}s"
          f"  |  barge-in {'on' if config.BARGE_IN_ENABLED else 'off'}")
    print(f"  Speaker   : {'verify on (enrolled)' if speaker_verify.enabled() else 'open — anyone (enroll with -m voice_assistant.enroll)'}")
    print("=" * 56)

    # Warm everything up front so the first interaction isn't slow.
    audio_out.warm()
    tts.warm()
    tts.prewarm(config.KNOWN_CONFIRMATIONS)  # pre-render fixed confirmations
    stt.warm()
    vad.warm()
    speaker_verify.warm()
    detector = WakeWordDetector()

    # Inbound channel: the brain pushes results of long, backgrounded tasks here.
    callback_server.start()

    stream = recorder.open_stream()
    ready = f"\n[ready] Listening for {config.WAKE_WORD!r}...\n"
    print(ready)

    try:
        while True:
            # speak any results the brain pushed back from a backgrounded task
            _deliver_pending(stream, detector)

            # ── wait for the wake word (or an external /wake request) ──
            frame = recorder.read_frame(stream)
            externally_woken = callback_server.wake_requested()
            if not detector.triggered(frame) and not externally_woken:
                continue

            print("[wake] external request" if externally_woken else "[wake] detected")
            playback.pause()  # pause other audio FIRST, before any feedback/listening
            tts.play_earcon()
            recorder.drain(stream)  # drop the earcon echo
            detector.reset()

            try:
                # ── first turn is wake-triggered (short start window) ──
                audio = recorder.record_utterance(stream)
                if audio is None:
                    print("[skip] no speech captured")

                # ── conversation loop: follow-ups need no wake word ──
                rejects = 0
                while audio is not None:
                    # Only act on the enrolled voice. Rejection is silent (no
                    # cue) — the point is that TV dialogue and other people
                    # never provoke a reaction. Re-open the listen window so a
                    # background voice can't end the user's conversation, but
                    # only a few times so continuous TV chatter drops to idle.
                    # isolate() also trims the clip to the user's own span, so
                    # TV dialogue around/after their command never reaches STT.
                    kept, sim = speaker_verify.isolate(audio)
                    if kept is None:
                        rejects += 1
                        print(f"[speaker] not the enrolled voice (sim {sim:.2f}) — ignoring")
                        if sim >= config.SPEAKER_THRESHOLD - 0.10:
                            print("  [speaker] close miss — if that was you, run:"
                                  " ./voice-venv/bin/python -m voice_assistant.enroll --add")
                        if rejects >= config.SPEAKER_MAX_REJECTS:
                            print("[speaker] too many rejected utterances — ending conversation")
                            break
                        audio = recorder.record_utterance(stream)
                        continue
                    if len(kept) < len(audio):
                        print(f"  [speaker] trimmed to your voice: "
                              f"{len(audio) / config.SAMPLE_RATE:.1f}s -> {len(kept) / config.SAMPLE_RATE:.1f}s")
                    audio = kept

                    text = stt.transcribe(audio)
                    if not text:
                        print("[end] empty transcript")
                        break
                    print(f"  You  : {text}")

                    if _is_stop_phrase(text):
                        print("[stop] ending conversation")
                        tts.speak("Okay.")
                        break

                    try:
                        response, status, music_touched, thread = _ask_with_thinking(text)
                    except Exception as e:
                        print(f"[error] brain request failed: {e}")
                        tts.speak("Sorry, I couldn't reach the brain.")
                        break
                    print(f"  Brain: {response}")

                    # Misroute guardrail: announce a resumed topic so the user
                    # can immediately say "no, new topic" if the routing missed.
                    if thread and thread.get("event") == "resumed" and thread.get("title"):
                        response = f"Picking up our conversation about {thread['title']}. {response}"

                    if music_touched:
                        # The agent changed music playback at the user's request
                        # ("pause the music", "play something"). Its state is now
                        # the user's intent — don't auto-resume over it at the end.
                        playback.release_claims()

                    interrupted = _speak(response, stream, detector)
                    recorder.drain(stream)  # drop the assistant's own voice

                    # Went async (or the brain was busy): no inline answer is
                    # coming this turn — the result will be spoken later via the
                    # callback. End the turn instead of holding the mic open for a
                    # follow-up; we drop back to wake-word idle where the pushed
                    # result gets spoken when it's ready.
                    if status in ("working", "busy"):
                        print("[async] brain working in background — ending turn; "
                              "result will be spoken when ready")
                        break

                    if interrupted:
                        # Wake word heard mid-reply — take the next command now.
                        print("[barge-in] interrupted — go ahead")
                        tts.play_earcon()
                        recorder.drain(stream)
                        playback.pause()  # re-pause for the new command
                        audio = recorder.record_utterance(stream)
                        continue

                    # follow-up window — listen without the wake word
                    if config.FOLLOWUP_CUE:
                        tts.play_listen_cue()
                        recorder.drain(stream)
                    playback.pause()  # re-pause: catch any audio the agent just started
                    print(f"  [listening for follow-up ~{config.FOLLOWUP_TIMEOUT:.0f}s...]")
                    audio = recorder.record_utterance(stream, start_timeout=config.FOLLOWUP_TIMEOUT)
                    if audio is None:
                        print("[end] no follow-up")
            finally:
                playback.resume()  # always bring the music back up

            detector.reset()
            print(ready)

    except KeyboardInterrupt:
        print("\n[exit] stopping...")
    finally:
        stream.stop()
        stream.close()
