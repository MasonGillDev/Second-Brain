"""Pause other audio during a conversation, resume it after.

Two layers:
  1. Reliable — Apple Music / Spotify via AppleScript. We check play-state, so we
     only ever resume what we actually paused, and never launch an app that
     wasn't running.
  2. Best-effort universal (PAUSE_SYSTEM) — simulate the Play/Pause media key to
     catch a browser/YouTube tab that isn't a scriptable app. macOS 26 locked
     down MediaRemote, so the simulated hardware key is the only universal lever.
     It's a toggle with no state read-back (see caveats in config), so we only
     use it when no scriptable app was the thing playing.

Replaces the old volume-ducking approach: pausing removes the audio at the
source, so nothing bleeds into speech-to-text.
"""

import subprocess

from . import config

_SCRIPTABLE = ["Music", "Spotify"]
_paused_apps: list[str] = []
_sent_system_key = False


def _osa(script: str) -> str | None:
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _running(app: str) -> bool:
    return _osa(f'tell application "System Events" to (name of processes) contains "{app}"') == "true"


def _is_playing(app: str) -> bool:
    if not _running(app):
        return False
    return _osa(f'tell application "{app}" to player state as string') == "playing"


def _send_media_key() -> bool:
    """Simulate the Play/Pause key (NX_KEYTYPE_PLAY). Toggles the system now-playing
    session — works for browsers/YouTube/etc. Returns False if unavailable."""
    try:
        from AppKit import NSEvent
        from Quartz import CGEventPost

        NX_KEYTYPE_PLAY = 16
        for down in (True, False):
            ev = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
                14,                                  # NSSystemDefined
                (0, 0),
                0xA00 if down else 0xB00,
                0, 0, None, 8,
                (NX_KEYTYPE_PLAY << 16) | ((0xA if down else 0xB) << 8),
                -1,
            )
            CGEventPost(0, ev.CGEvent())            # 0 = kCGHIDEventTap
        return True
    except Exception as e:
        print(f"  [pause] system media key unavailable: {e}")
        return False


def pause() -> None:
    """Pause other audio for the duration of a conversation. Idempotent — safe to
    call before each listen window (catches audio the agent just started)."""
    global _sent_system_key
    if not config.PAUSE_ENABLED:
        return

    paused_scriptable = bool(_paused_apps)
    for app in _SCRIPTABLE:
        if app in _paused_apps:
            continue
        if _is_playing(app):
            _osa(f'tell application "{app}" to pause')
            _paused_apps.append(app)
            paused_scriptable = True
            print(f"  [pause] {app}")

    # The media key is a blind play/pause TOGGLE (macOS 26 gives no way to read
    # play-state). Only fire it when NO scriptable app is even running: if Music
    # or Spotify is open it's likely the now-playing session, and a toggle would
    # RESUME it when it's paused (exactly the "music turned on when I spoke" bug).
    # With Music/Spotify closed, the now-playing session is a browser/YouTube tab,
    # and the toggle pauses it as intended.
    if (config.PAUSE_SYSTEM and not paused_scriptable and not _sent_system_key
            and not any(_running(a) for a in _SCRIPTABLE)):
        if _send_media_key():
            _sent_system_key = True
            print("  [pause] system media key (browser/other)")


def release_claims() -> None:
    """Forget that we paused Music/Spotify — called when the agent changed music
    playback during the conversation (user said "pause the music", "play
    something", ...). The user's expressed intent now owns the state, so the
    end-of-conversation resume() must not override it. If the agent *started*
    music, the re-pause before the next listen window will observe it playing
    and take a fresh claim, so it still resumes correctly afterwards.

    Deliberately leaves the media-key state alone: that claim is about a
    browser tab, which the music tools don't touch."""
    if _paused_apps:
        print(f"  [pause] agent changed music — releasing claim on {_paused_apps}")
        _paused_apps.clear()


def resume() -> None:
    """Resume whatever we paused when the conversation ends."""
    global _sent_system_key
    for app in _paused_apps:
        if _running(app):
            _osa(f'tell application "{app}" to play')
            print(f"  [resume] {app}")
    _paused_apps.clear()
    if _sent_system_key:
        _send_media_key()
        _sent_system_key = False
        print("  [resume] system media key")
