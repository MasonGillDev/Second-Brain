"""
macOS window placement.

Launches apps and moves/resizes their windows across displays via AppleScript
(System Events). Two coordinate systems are in play and they disagree:

  * NSScreen  — used to enumerate displays. Bottom-left origin.
  * System Events — used to move windows. Top-left origin.

Everything below is normalized to top-left (screen 0's top-left is 0,0), so
callers never see the flip. Screen rects come from `visibleFrame`, meaning the
menu bar and Dock are already excluded — a "full" placement won't slide under them.

Requires Accessibility permission for whichever process runs this.
"""

import json
import subprocess
import time

# Named placements as fractions of a screen's visible frame: (x, y, w, h).
PRESETS = {
    "full":         (0.0,  0.0,  1.0,  1.0),
    "left":         (0.0,  0.0,  0.5,  1.0),
    "right":        (0.5,  0.0,  0.5,  1.0),
    "top":          (0.0,  0.0,  1.0,  0.5),
    "bottom":       (0.0,  0.5,  1.0,  0.5),
    "top-left":     (0.0,  0.0,  0.5,  0.5),
    "top-right":    (0.5,  0.0,  0.5,  0.5),
    "bottom-left":  (0.0,  0.5,  0.5,  0.5),
    "bottom-right": (0.5,  0.5,  0.5,  0.5),
    "center":       (0.15, 0.10, 0.7,  0.8),
    "left-third":   (0.0,  0.0,  1 / 3, 1.0),
    "middle-third": (1 / 3, 0.0, 1 / 3, 1.0),
    "right-third":  (2 / 3, 0.0, 1 / 3, 1.0),
    "left-two-thirds":  (0.0,   0.0, 2 / 3, 1.0),
    "right-two-thirds": (1 / 3, 0.0, 2 / 3, 1.0),
}


class WindowError(RuntimeError):
    """Placement failed in a way the caller should surface to the user."""


def _osascript(script: str, lang: str = "AppleScript", timeout: int = 30) -> str:
    args = ["osascript"]
    if lang == "JavaScript":
        args += ["-l", "JavaScript"]
    args += ["-e", script]
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise WindowError(result.stderr.strip() or "osascript failed")
    return result.stdout.strip()


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def list_screens() -> list[dict]:
    """All displays, as top-left-origin visible rects. Index 0 is the primary."""
    raw = _osascript(
        """
        ObjC.import("AppKit");
        var s = $.NSScreen.screens, out = [];
        var primaryH = s.objectAtIndex(0).frame.size.height;
        for (var i = 0; i < s.count; i++) {
          var sc = s.objectAtIndex(i), v = sc.visibleFrame;
          out.push({
            index: i,
            name: ObjC.unwrap(sc.localizedName),
            x: v.origin.x,
            // NSScreen measures y up from the bottom of the primary display;
            // System Events measures down from its top. Flip.
            y: primaryH - (v.origin.y + v.size.height),
            width: v.size.width,
            height: v.size.height
          });
        }
        JSON.stringify(out);
        """,
        lang="JavaScript",
    )
    return [{k: (int(v) if isinstance(v, float) else v) for k, v in s.items()}
            for s in json.loads(raw)]


def resolve_screen(screen) -> dict:
    """
    Resolve a screen reference to a screen dict.

    Accepts an index (0, 1, ...), a name fragment ("LG", "Built-in"), the aliases
    "main"/"primary" and "builtin"/"laptop", or None (primary).
    """
    screens = list_screens()
    if screen is None:
        return screens[0]

    if isinstance(screen, int) or (isinstance(screen, str) and screen.lstrip("-").isdigit()):
        idx = int(screen)
        if not 0 <= idx < len(screens):
            raise WindowError(
                f"No screen {idx}. {len(screens)} connected: "
                + ", ".join(f"{s['index']}={s['name']}" for s in screens)
            )
        return screens[idx]

    key = str(screen).strip().lower()
    if key in ("main", "primary", "default"):
        return screens[0]
    if key in ("builtin", "built-in", "laptop", "internal"):
        for s in screens:
            if "built-in" in s["name"].lower() or "liquid retina" in s["name"].lower():
                return s
        raise WindowError("Built-in display isn't active (lid shut or clamshell mode).")

    for s in screens:
        if key in s["name"].lower():
            return s
    raise WindowError(
        f"No screen matching '{screen}'. Connected: "
        + ", ".join(f"{s['index']}={s['name']}" for s in screens)
    )


def resolve_position(position, screen: dict) -> tuple[int, int, int, int]:
    """Turn a preset name or "x,y,w,h" fraction string into absolute pixels."""
    if position is None:
        position = "full"
    key = str(position).strip().lower()

    if key in PRESETS:
        fx, fy, fw, fh = PRESETS[key]
    else:
        parts = [p.strip() for p in key.replace(" ", "").split(",")]
        if len(parts) != 4:
            raise WindowError(
                f"Unknown position '{position}'. Use a preset "
                f"({', '.join(sorted(PRESETS))}) or four fractions 'x,y,w,h'."
            )
        try:
            fx, fy, fw, fh = (float(p) for p in parts)
        except ValueError:
            raise WindowError(f"Position fractions must be numbers, got '{position}'.")

    return (
        round(screen["x"] + screen["width"] * fx),
        round(screen["y"] + screen["height"] * fy),
        round(screen["width"] * fw),
        round(screen["height"] * fh),
    )


def list_windows() -> list[dict]:
    """Open windows of visible (non-background) apps, with the screen each is on."""
    raw = _osascript(
        """
        ObjC.import("AppKit");
        var se = Application("System Events"), out = [];
        var procs = se.applicationProcesses.whose({
          visible: true, backgroundOnly: false
        })();
        for (var i = 0; i < procs.length; i++) {
          var p = procs[i], wins;
          try { wins = p.windows(); } catch (e) { continue; }
          for (var j = 0; j < wins.length; j++) {
            try {
              var pos = wins[j].position(), size = wins[j].size();
              out.push({app: p.name(), title: wins[j].name(), index: j + 1,
                        x: pos[0], y: pos[1], width: size[0], height: size[1]});
            } catch (e) {}
          }
        }
        JSON.stringify(out);
        """,
        lang="JavaScript",
    )
    windows = json.loads(raw)
    screens = list_screens()
    for w in windows:
        # A window belongs to the screen containing its center point; fall back to
        # primary for windows dragged mostly off-screen.
        cx, cy = w["x"] + w["width"] / 2, w["y"] + w["height"] / 2
        w["screen"] = next(
            (s["index"] for s in screens
             if s["x"] <= cx < s["x"] + s["width"] and s["y"] <= cy < s["y"] + s["height"]),
            0,
        )
    return windows


def resolve_app(name: str) -> str:
    """
    Map a user-facing app name to the process name System Events knows it by.

    These usually match but not always, and a wrong name yields a confusing
    AppleScript error, so match against what's actually running.
    """
    raw = _osascript(
        'tell application "System Events" to get name of every process '
        "whose visible is true and background only is false"
    )
    procs = [p.strip() for p in raw.split(",") if p.strip()]
    key = name.strip().lower()

    for p in procs:                                    # exact
        if p.lower() == key:
            return p
    for p in procs:                                    # prefix ("Chrome" → "Google Chrome")
        if p.lower().startswith(key) or key.startswith(p.lower()):
            return p
    for p in procs:                                    # substring
        if key in p.lower() or p.lower() in key:
            return p
    raise WindowError(
        f"'{name}' isn't running (or has no visible windows). Running: "
        + ", ".join(sorted(procs))
    )


def _place(process: str, x: int, y: int, w: int, h: int,
           window_index: int = 1, wait: float = 0.0) -> dict:
    """
    Move/resize a window and report where it actually landed.

    AppleScript *requests* geometry; an app may clamp or ignore it (Music won't go
    below ~980px wide, Xcode ignores some resizes). Returning the real rect lets
    the caller tell the user the truth instead of assuming success.
    """
    attempts = max(1, int(wait / 0.25)) if wait else 1
    script = f"""
on run argv
  set p to "{_escape(process)}"
  tell application "System Events"
    repeat {attempts} times
      try
        if (count of windows of process p) >= {window_index} then
          tell window {window_index} of process p
            set position to {{{x}, {y}}}
            set size to {{{w}, {h}}}
            delay 0.05
            set finalPos to position
            set finalSize to size
          end tell
          return ((item 1 of finalPos) as text) & "," & ((item 2 of finalPos) as text) ¬
            & "," & ((item 1 of finalSize) as text) & "," & ((item 2 of finalSize) as text)
        end if
      end try
      delay 0.25
    end repeat
    error "no window {window_index} for " & p
  end tell
end run
"""
    got = [int(float(v)) for v in _osascript(script).split(",")]
    return {
        "requested": {"x": x, "y": y, "width": w, "height": h},
        "actual": {"x": got[0], "y": got[1], "width": got[2], "height": got[3]},
        # Apps that clamp to a minimum size are the common cause of a mismatch.
        "exact": got == [x, y, w, h],
    }


def position_app(app: str, screen=None, position="full", window_index: int = 1) -> dict:
    """Move an already-running app's window. Raises if the app isn't running."""
    process = resolve_app(app)
    scr = resolve_screen(screen)
    x, y, w, h = resolve_position(position, scr)
    result = _place(process, x, y, w, h, window_index)
    result.update({"app": process, "screen": scr["index"], "screen_name": scr["name"],
                   "position": position})
    return result


def open_app(app: str, screen=None, position=None, new_instance: bool = False) -> dict:
    """
    Launch (or focus) an app, optionally placing its window.

    With no position the app just opens wherever macOS puts it. With one, we wait
    for the window to exist rather than sleeping a fixed amount — launch times
    range from Safari's instant to Ableton's many seconds.
    """
    cmd = ["open", "-na" if new_instance else "-a", app]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise WindowError(proc.stderr.strip() or f"macOS could not launch '{app}'")

    if position is None and screen is None:
        return {"app": app, "opened": True, "positioned": False}

    scr = resolve_screen(screen)
    x, y, w, h = resolve_position(position, scr)

    # Give the app time to register a process before matching its name.
    process, last_error = None, None
    for _ in range(40):
        try:
            process = resolve_app(app)
            break
        except WindowError as e:
            last_error = e
            time.sleep(0.25)
    if process is None:
        raise WindowError(f"'{app}' opened but never showed a window: {last_error}")

    result = _place(process, x, y, w, h, wait=15.0)
    result.update({"app": process, "opened": True, "positioned": True,
                   "screen": scr["index"], "screen_name": scr["name"],
                   "position": position or "full"})
    return result
