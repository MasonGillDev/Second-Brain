"""
Window management MCP Server.

Opens apps and places their windows on specific displays. All logic lives in
app/window_manager.py; this file only maps it to tools and phrases results.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from window_manager import (
    PRESETS,
    WindowError,
    list_screens as _list_screens,
    list_windows as _list_windows,
    open_app as _open_app,
    position_app as _position_app,
)

mcp = FastMCP("windows")

_PRESET_HELP = ", ".join(sorted(PRESETS))


def _describe(result: dict) -> str:
    """Phrase a placement result, calling out any geometry the app refused."""
    a, r = result["actual"], result["requested"]
    where = f"screen {result['screen']} ({result['screen_name']}), {result['position']}"
    line = f"{result['app']} → {where} — {a['width']}x{a['height']} at {a['x']},{a['y']}"
    if not result["exact"]:
        line += (
            f" (asked for {r['width']}x{r['height']} at {r['x']},{r['y']}; "
            "the app clamped it — many apps enforce a minimum window size)"
        )
    return line


def open_app(
    app: str,
    screen: str = "",
    position: str = "",
    new_window: bool = False,
    new_instance: bool = False,
) -> str:
    """
    Open (or focus) a Mac app, optionally placing its window on a specific display.

    Use this when the app may not be running yet. If it is already open and you
    just want to move it, use position_app instead to avoid stealing focus.

    To tile SEVERAL windows of the same app (e.g. four Terminals, one per corner),
    call this once per window with new_window=True. Without that flag, opening an
    app that is already running only focuses its existing window, so each call
    would move that same window instead of making new ones.

    Args:
        app: App name as it appears in /Applications, e.g. "Safari", "Ableton Live 12".
        screen: Which display. A number ("0", "1"), a name fragment ("LG"), "main",
                or "builtin". Empty means the main display. Call list_screens first
                if you need to know what's connected.
        position: Where on that screen. A preset — one of: {presets} — or four
                  fractions "x,y,w,h" of the screen (e.g. "0.25,0,0.5,0.6").
                  Empty with no screen given means "open it, don't move it".
        new_window: Make a NEW window instead of reusing the app's existing one.
                    Required when tiling multiple windows of one app.
        new_instance: Launch a second copy of the app entirely. Rarely wanted —
                      prefer new_window.
    """
    try:
        result = _open_app(
            app,
            screen=screen or None,
            position=position or None,
            new_window=new_window,
            new_instance=new_instance,
        )
    except WindowError as e:
        return f"Could not open '{app}': {e}"

    verb = "Opened new window of" if result.get("new_window") else "Opened"
    if not result.get("positioned"):
        return f"{verb} {result['app']} (left it wherever macOS put it)."
    return f"{verb} " + _describe(result)




def position_app(
    app: str,
    screen: str = "",
    position: str = "full",
    window_index: int = 1,
) -> str:
    """
    Move and resize an already-open app's window. Does not launch anything and
    does not steal focus.

    Args:
        app: App name — matched against what is actually running, so "Chrome"
             finds "Google Chrome". Call list_windows to see open apps.
        screen: Which display. A number ("0", "1"), a name fragment ("LG"), "main",
                or "builtin". Empty means the main display.
        position: A preset — one of: {presets} — or four fractions "x,y,w,h" of the
                  screen (e.g. "0.25,0,0.5,0.6").
        window_index: Which window if the app has several (1 = frontmost).
    """
    try:
        result = _position_app(app, screen=screen or None, position=position,
                               window_index=window_index)
    except WindowError as e:
        msg = str(e)
        if "no window" in msg:
            return (
                f"'{app}' is running but has no open window to move "
                "(it may be minimized or closed to the menu bar). "
                "Use open_app to give it one."
            )
        return f"Could not move '{app}': {msg}"
    return "Moved " + _describe(result)




# The preset list belongs in the schema the model reads, but writing it inline
# would duplicate window_manager.PRESETS. Format it in, then register — @mcp.tool()
# snapshots __doc__ when it runs, so this has to happen before registration.
for _fn in (open_app, position_app):
    _fn.__doc__ = _fn.__doc__.format(presets=_PRESET_HELP)
    mcp.tool()(_fn)


@mcp.tool()
def list_screens() -> str:
    """
    List connected displays with their index, name and usable area.

    Call this before placing a window when you are unsure how many displays are
    attached — a laptop in clamshell mode has only one, so "screen 1" would fail.
    """
    try:
        screens = _list_screens()
    except WindowError as e:
        return f"Could not read displays: {e}"
    return "\n".join(
        f"{s['index']}: {s['name']} — {s['width']}x{s['height']} usable at {s['x']},{s['y']}"
        + (" (main)" if s["index"] == 0 else "")
        for s in screens
    )


@mcp.tool()
def list_windows() -> str:
    """
    List every open window — app, title, size, position, and which screen it is on.

    Use this to find the exact app name before calling position_app, or to see the
    current layout before rearranging it.
    """
    try:
        windows = _list_windows()
    except WindowError as e:
        return f"Could not read windows: {e}"
    if not windows:
        return "No open windows."

    lines = []
    for w in windows:
        title = (w["title"] or "").strip()
        if len(title) > 50:
            title = title[:47] + "..."
        lines.append(
            f"{w['app']}" + (f" — {title}" if title else "")
            + f" [screen {w['screen']}, {w['width']}x{w['height']} at {w['x']},{w['y']}]"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
