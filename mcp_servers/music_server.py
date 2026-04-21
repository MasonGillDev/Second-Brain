"""
Apple Music MCP Server.

Controls Apple Music via AppleScript. Supports playback,
search, playlists, and track info.
"""

import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("music")


def run_applescript(script: str) -> str:
    """Run an AppleScript and return the output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def _escape(text: str) -> str:
    """Escape a string for use in AppleScript."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


@mcp.tool()
def play(query: str) -> str:
    """
    Play a song, album, artist, or playlist by name.
    Searches your library and plays the first match.

    Args:
        query: What to play — a song name, artist, album, or playlist name.
               Examples: "Bohemian Rhapsody", "Drake", "Abbey Road"
    """
    escaped = _escape(query)

    # First try matching a playlist (handles trailing whitespace in names)
    try:
        result = run_applescript(f'''
tell application "Music"
    set q to "{escaped}"
    repeat with p in (every playlist)
        set pName to name of p
        -- Trim trailing spaces
        repeat while pName ends with " "
            set pName to text 1 thru -2 of pName
        end repeat
        if pName is q then
            play p
            return "Playing playlist: " & pName
        end if
    end repeat
    return "NO_PLAYLIST"
end tell''')
        if result != "NO_PLAYLIST":
            return result
    except RuntimeError:
        pass

    # Then search the library for tracks
    try:
        result = run_applescript(f'''
tell application "Music"
    set results to search playlist "Library" for "{escaped}"
    if results is not {{}} then
        play item 1 of results
        set t to item 1 of results
        return "Playing: " & (name of t) & " by " & (artist of t) & " from " & (album of t)
    else
        return "NOT_FOUND"
    end if
end tell''')
        if result == "NOT_FOUND":
            return f"No results found for '{query}' in your library. Try a different search term."
        return result
    except RuntimeError as e:
        return f"Could not play '{query}': {e}"


@mcp.tool()
def pause() -> str:
    """Pause playback."""
    run_applescript('tell application "Music" to pause')
    return "Paused."


@mcp.tool()
def resume() -> str:
    """Resume playback."""
    run_applescript('tell application "Music" to play')
    return "Resumed."


@mcp.tool()
def skip() -> str:
    """Skip to the next track."""
    run_applescript('tell application "Music" to next track')
    try:
        return now_playing()
    except Exception:
        return "Skipped to next track."


@mcp.tool()
def previous() -> str:
    """Go back to the previous track."""
    run_applescript('tell application "Music" to previous track')
    try:
        return now_playing()
    except Exception:
        return "Went to previous track."


@mcp.tool()
def now_playing() -> str:
    """Get info about the currently playing track."""
    try:
        result = run_applescript('''
tell application "Music"
    if player state is not stopped then
        set t to current track
        set pos to player position as integer
        set dur to duration of t as integer
        set mins to pos div 60
        set secs to pos mod 60
        set dmins to dur div 60
        set dsecs to dur mod 60
        set timeStr to (mins as text) & ":" & text -2 thru -1 of ("0" & (secs as text))
        set durStr to (dmins as text) & ":" & text -2 thru -1 of ("0" & (dsecs as text))
        return (name of t) & " | " & (artist of t) & " | " & (album of t) & " | " & timeStr & "/" & durStr & " | " & (player state as text)
    else
        return "Nothing playing."
    end if
end tell''')
        if result == "Nothing playing.":
            return result
        parts = result.split(" | ")
        if len(parts) >= 5:
            return (f"Track: {parts[0]}\n"
                    f"Artist: {parts[1]}\n"
                    f"Album: {parts[2]}\n"
                    f"Position: {parts[3]}\n"
                    f"State: {parts[4]}")
        return result
    except RuntimeError as e:
        return f"Could not get track info: {e}"


@mcp.tool()
def search_library(query: str, limit: int = 10) -> str:
    """
    Search your Apple Music library.

    Args:
        query: Search term (song name, artist, album).
        limit: Max results to return (default 10).
    """
    escaped = _escape(query)
    result = run_applescript(f'''
tell application "Music"
    set results to search playlist "Library" for "{escaped}"
    set output to ""
    set maxCount to {limit}
    if (count of results) < maxCount then set maxCount to (count of results)
    repeat with i from 1 to maxCount
        set t to item i of results
        set output to output & (name of t) & " — " & (artist of t) & " [" & (album of t) & "]" & linefeed
    end repeat
    return output
end tell''')
    if not result:
        return f"No results for '{query}'."
    return f"Found in library:\n{result}"


@mcp.tool()
def list_playlists() -> str:
    """List all your playlists."""
    result = run_applescript('''
tell application "Music"
    return name of every playlist
end tell''')
    if not result:
        return "No playlists found."
    # Parse comma-separated AppleScript list
    names = [n.strip() for n in result.split(",")]
    return "Playlists:\n" + "\n".join(f"- {n}" for n in names)


@mcp.tool()
def play_playlist(name: str, shuffle: bool = False) -> str:
    """
    Play a specific playlist.

    Args:
        name: Name of the playlist.
        shuffle: If true, shuffle the playlist.
    """
    escaped = _escape(name)
    shuffle_cmd = 'set shuffle enabled to true' if shuffle else 'set shuffle enabled to false'
    try:
        result = run_applescript(f'''
tell application "Music"
    set q to "{escaped}"
    repeat with p in (every playlist)
        set pName to name of p
        repeat while pName ends with " "
            set pName to text 1 thru -2 of pName
        end repeat
        if pName is q then
            {shuffle_cmd}
            play p
            return "Playing playlist: " & pName
        end if
    end repeat
    return "NOT_FOUND"
end tell''')
        if result == "NOT_FOUND":
            return f"Could not find playlist '{name}'."
        mode = " (shuffled)" if shuffle else ""
        return result + mode
    except RuntimeError as e:
        return f"Could not play playlist '{name}': {e}"


@mcp.tool()
def set_volume(level: int) -> str:
    """
    Set the Apple Music volume.

    Args:
        level: Volume level from 0 (mute) to 100 (max).
    """
    level = max(0, min(100, level))
    run_applescript(f'tell application "Music" to set sound volume to {level}')
    return f"Volume set to {level}."


@mcp.tool()
def add_to_playlist(playlist_name: str, song_query: str) -> str:
    """
    Add a song to a playlist by searching for it.

    Args:
        playlist_name: Name of the playlist to add to.
        song_query: Search term to find the song.
    """
    p_escaped = _escape(playlist_name)
    s_escaped = _escape(song_query)
    try:
        result = run_applescript(f'''
tell application "Music"
    set results to search playlist "Library" for "{s_escaped}"
    if results is {{}} then return "NOT_FOUND"
    set t to item 1 of results
    duplicate t to playlist "{p_escaped}"
    return "Added: " & (name of t) & " by " & (artist of t) & " to {p_escaped}"
end tell''')
        if result == "NOT_FOUND":
            return f"No song found for '{song_query}'."
        return result
    except RuntimeError as e:
        return f"Error: {e}"


@mcp.tool()
def list_airplay_devices() -> str:
    """List all available AirPlay devices and their current status."""
    result = run_applescript('''
tell application "Music"
    set output to ""
    repeat with d in (every AirPlay device)
        set devName to name of d
        set devSelected to selected of d
        set devVol to sound volume of d
        if devSelected then
            set status to "ON"
        else
            set status to "OFF"
        end if
        set output to output & devName & " | " & status & " | vol:" & devVol & linefeed
    end repeat
    return output
end tell''')
    if not result:
        return "No AirPlay devices found."
    lines = []
    for line in result.strip().split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            icon = "🔊" if parts[1] == "ON" else "  "
            lines.append(f"{icon} {parts[0]} [{parts[1]}] {parts[2]}")
    return "AirPlay Devices:\n" + "\n".join(lines)


@mcp.tool()
def set_airplay(device_name: str, enabled: bool = True) -> str:
    """
    Enable or disable an AirPlay device for playback.
    You can enable multiple devices at once for multi-room audio.

    Args:
        device_name: Name of the AirPlay device (e.g., "Kitchen", "Living Room").
        enabled: True to play on this device, False to stop.
    """
    escaped = _escape(device_name)
    state = "true" if enabled else "false"
    try:
        result = run_applescript(f'''
tell application "Music"
    set q to "{escaped}"
    repeat with d in (every AirPlay device)
        set dName to name of d
        -- Trim trailing spaces
        repeat while dName ends with " "
            set dName to text 1 thru -2 of dName
        end repeat
        if dName is q then
            set selected of d to {state}
            return "AirPlay " & dName & " set to {state}"
        end if
    end repeat
    return "NOT_FOUND"
end tell''')
        if result == "NOT_FOUND":
            return f"No AirPlay device named '{device_name}'. Use list_airplay_devices to see available devices."
        return result
    except RuntimeError as e:
        return f"Error: {e}"


@mcp.tool()
def set_airplay_volume(device_name: str, level: int) -> str:
    """
    Set the volume for a specific AirPlay device.

    Args:
        device_name: Name of the AirPlay device.
        level: Volume level from 0 (mute) to 100 (max).
    """
    escaped = _escape(device_name)
    level = max(0, min(100, level))
    try:
        result = run_applescript(f'''
tell application "Music"
    set q to "{escaped}"
    repeat with d in (every AirPlay device)
        set dName to name of d
        repeat while dName ends with " "
            set dName to text 1 thru -2 of dName
        end repeat
        if dName is q then
            set sound volume of d to {level}
            return "Volume for " & dName & " set to {level}"
        end if
    end repeat
    return "NOT_FOUND"
end tell''')
        if result == "NOT_FOUND":
            return f"No AirPlay device named '{device_name}'."
        return result
    except RuntimeError as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
