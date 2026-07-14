# Second Brain — Device Folder Watcher

A tiny background service that runs on your devices (PC, MacBook) and pushes
documents into Second Brain automatically. Drop a `.md` or `.docx` file into a
watched folder → it lands on the Mac mini, gets ingested, and is instantly
searchable by the agent.

## How it works

```
   watched folder ──(file lands/changes)──► watcher.py ──HTTP POST──►  Mac mini
                                                                    /api/ingest/upload
                                                                    → saved to docs dir
                                                                    → ingested immediately
```

The watcher also **registers** with the brain and **heartbeats** every 60s, so
the dashboard's **Devices** tab shows it as online with its watched folders and
files-sent count.

## Setup (both platforms)

1. Install Python 3.10+ and the two dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy the example config and edit it:
   ```
   cp config.example.json config.json
   ```
   - `server_url` — the mini's Tailscale address: `http://100.103.102.56:5001`
     (works from any network). Use the LAN IP only if you never leave home.
   - `api_key` — on **macOS**, leave it as `"keychain"` (reads the
     `ingest-api-key` secret from Keychain, never stored on disk). On **Windows**,
     paste the actual token string.
   - `watch_paths` — the folders to watch. **To add a folder later: add it here
     and restart the watcher.**
3. Run it:
   ```
   python watcher.py
   ```
   On first run it scans your watch folders and uploads anything new, then waits
   for changes.

### Getting the token onto Windows

macOS reads the token from Keychain automatically. For the Windows PC, on the
Mac mini run:

```
security find-generic-password -a "$(whoami)" -s ingest-api-key -w
```

Copy that value into `api_key` in the Windows `config.json`. Keep it private.

## Run at login

### macOS (launchd)

Create `~/Library/LaunchAgents/com.masongill.brainwatcher.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.masongill.brainwatcher</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/path/to/Second-Brain/device_watcher/watcher.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/brainwatcher.log</string>
  <key>StandardErrorPath</key><string>/tmp/brainwatcher.err</string>
</dict>
</plist>
```

Then:
```
launchctl load ~/Library/LaunchAgents/com.masongill.brainwatcher.plist
```

### Windows (Task Scheduler)

Create a task that runs at logon:
```
schtasks /Create /SC ONLOGON /TN BrainWatcher /TR "pythonw C:\path\to\device_watcher\watcher.py" /RL LIMITED
```
Use `pythonw` (not `python`) so it runs without a console window.

## Notes & limits

- **Supported types:** `.md` and `.docx`. Other files are ignored locally and
  rejected by the server.
- **Updates:** editing a file re-uploads it; the brain replaces the old version.
- **Filename = identity:** two devices with the same filename but different
  content will overwrite each other in the brain. Rename, or ask for per-device
  namespacing.
- **Deletes are not propagated:** removing a local file leaves its content in the
  brain. Delete it from the dashboard's Memories → documents if you want it gone.
- **State file:** `.watcher_state.json` remembers what's been uploaded. Delete it
  to force a full re-upload on next start.
