"""
Second Brain — device folder watcher.

Runs on each of your devices (PC, MacBook). Watches the folders listed in
config.json and, whenever a supported file lands or changes, uploads it to the
Second Brain ingest endpoint over your network (Tailscale/LAN). The brain saves
it and ingests it immediately, so it becomes searchable right away.

Config is a plain JSON file (config.json next to this script, or set the
BRAIN_WATCHER_CONFIG env var). To add a folder: add it to "watch_paths" and
restart the watcher.

Design notes:
  - Debounce: editors emit many write events per save (and some save atomically
    via temp-file + rename). We wait until a file's size has been stable for a
    couple seconds before uploading, so we never send a half-written file.
  - Local sent-state (.watcher_state.json): remembers the content hash we last
    uploaded per path, so a restart doesn't re-blast unchanged files. The server
    also hash-skips duplicates, so this is just to save bandwidth.
  - Updates: re-saving a file with the same name and new content re-uploads it;
    the server replaces the old chunks (keyed by filename). Deletes are NOT
    propagated — removing a local file leaves its chunks in the brain.

Requires: requests, watchdog  (pip install -r requirements.txt)
"""

import hashlib
import json
import os
import platform as pyplatform
import socket
import sys
import threading
import time

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("BRAIN_WATCHER_CONFIG", os.path.join(_HERE, "config.json"))
STATE_PATH = os.path.join(_HERE, ".watcher_state.json")

DEBOUNCE_SECONDS = 2.0      # file size must be stable this long before upload
HEARTBEAT_SECONDS = 60      # liveness ping interval
POLL_INTERVAL = 1.0         # debounce worker tick


# --------------------------------------------------------------------------- #
# Config + helpers
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        sys.exit(f"No config found at {CONFIG_PATH}. Copy config.example.json to "
                 f"config.json and edit it.")
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    cfg.setdefault("extensions", [".md", ".docx"])
    cfg.setdefault("recursive", True)
    cfg["extensions"] = [e.lower() for e in cfg["extensions"]]
    if not cfg.get("server_url") or not cfg.get("watch_paths"):
        sys.exit("config.json must set 'server_url' and a non-empty 'watch_paths'.")
    return cfg


def resolve_api_key(cfg: dict) -> str:
    """The token may be the literal string, or 'keychain' to read the
    'ingest-api-key' secret from macOS Keychain (so it's never on disk)."""
    key = (cfg.get("api_key") or "").strip()
    if key.lower() == "keychain":
        if pyplatform.system() != "Darwin":
            sys.exit("api_key 'keychain' is macOS-only; paste the token on this OS.")
        import subprocess
        user = subprocess.getoutput("whoami")
        r = subprocess.run(
            ["security", "find-generic-password", "-a", user, "-s", "ingest-api-key", "-w"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            sys.exit(f"Keychain lookup for 'ingest-api-key' failed: {r.stderr.strip()}")
        return r.stdout.strip()
    if not key:
        sys.exit("config.json must set 'api_key' (the token, or 'keychain' on macOS).")
    return key


def device_id() -> str:
    return socket.gethostname().split(".")[0].lower()


def file_hash(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except OSError:
        return None


def load_state() -> dict:
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_PATH)


# --------------------------------------------------------------------------- #
# Uploader — talks to the brain
# --------------------------------------------------------------------------- #

class Uploader:
    def __init__(self, cfg: dict, api_key: str):
        self.base = cfg["server_url"].rstrip("/")
        self.did = device_id()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "X-Device-Id": self.did,
        })
        self._state = load_state()
        self._state_lock = threading.Lock()

    def register(self, cfg: dict) -> None:
        payload = {
            "device_id": self.did,
            "hostname": socket.gethostname(),
            "platform": pyplatform.system().lower(),
            "watch_paths": cfg["watch_paths"],
        }
        try:
            self.session.post(f"{self.base}/api/ingest/register", json=payload, timeout=10)
            print(f"[watcher] registered as '{self.did}' with the brain")
        except requests.RequestException as e:
            print(f"[watcher] register failed (will retry via heartbeat): {e}")

    def heartbeat(self) -> None:
        try:
            self.session.post(f"{self.base}/api/ingest/heartbeat",
                              json={"device_id": self.did}, timeout=10)
        except requests.RequestException:
            pass

    def upload(self, path: str) -> None:
        """Upload one file if its content changed since we last sent it."""
        h = file_hash(path)
        if h is None:
            return  # vanished / unreadable
        with self._state_lock:
            if self._state.get(path) == h:
                return  # already sent this exact content

        name = os.path.basename(path)
        try:
            with open(path, "rb") as fh:
                r = self.session.post(
                    f"{self.base}/api/ingest/upload",
                    files={"file": (name, fh)}, timeout=60,
                )
        except (requests.RequestException, OSError) as e:
            print(f"[watcher] upload failed for {name}: {e}")
            return

        if r.status_code == 200:
            added = r.json().get("chunks_added")
            print(f"[watcher] sent {name} ({added} chunks)")
            with self._state_lock:
                self._state[path] = h
                save_state(self._state)
        elif r.status_code == 415:
            print(f"[watcher] server rejected {name} (unsupported type) — skipping")
            with self._state_lock:  # record so we don't retry it forever
                self._state[path] = h
                save_state(self._state)
        else:
            print(f"[watcher] upload of {name} -> HTTP {r.status_code}: {r.text[:200]}")


# --------------------------------------------------------------------------- #
# Filesystem watching + debounce
# --------------------------------------------------------------------------- #

class DebounceHandler(FileSystemEventHandler):
    """Records candidate files; the debounce worker decides when they're stable
    enough to upload."""

    def __init__(self, pending: dict, lock: threading.Lock, extensions: list[str]):
        self.pending = pending
        self.lock = lock
        self.exts = extensions

    def _consider(self, path: str) -> None:
        if os.path.isdir(path):
            return
        if os.path.splitext(path)[1].lower() not in self.exts:
            return
        with self.lock:
            self.pending[path] = (time.time(), -1)  # (last_event_ts, last_seen_size)

    def on_created(self, event):
        if not event.is_directory:
            self._consider(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._consider(event.src_path)

    def on_moved(self, event):
        # Atomic saves land here (temp -> real name). Care about the destination.
        dest = getattr(event, "dest_path", None)
        if dest:
            self._consider(dest)


def debounce_worker(pending: dict, lock: threading.Lock, uploader: Uploader,
                    stop: threading.Event) -> None:
    """Upload files once their size has been stable for DEBOUNCE_SECONDS."""
    while not stop.is_set():
        time.sleep(POLL_INTERVAL)
        now = time.time()
        due = []
        with lock:
            for path, (ts, last_size) in list(pending.items()):
                if now - ts < DEBOUNCE_SECONDS:
                    continue
                try:
                    size = os.path.getsize(path)
                except OSError:
                    pending.pop(path, None)  # gone
                    continue
                if size != last_size:
                    pending[path] = (now, size)  # still changing — re-arm
                    continue
                due.append(path)
                pending.pop(path, None)
        for path in due:
            uploader.upload(path)


def initial_scan(cfg: dict, uploader: Uploader) -> None:
    """Catch files that were added/changed while the watcher was off. The sent-
    state + server hash-skip make unchanged files free, so this only uploads new
    or modified content."""
    exts = cfg["extensions"]
    for root_path in cfg["watch_paths"]:
        if not os.path.isdir(root_path):
            print(f"[watcher] watch path not found (skipping): {root_path}")
            continue
        walker = os.walk(root_path) if cfg["recursive"] else [(root_path, [], os.listdir(root_path))]
        for dirpath, _dirs, files in walker:
            for name in files:
                if os.path.splitext(name)[1].lower() in exts:
                    uploader.upload(os.path.join(dirpath, name))


def main() -> None:
    cfg = load_config()
    api_key = resolve_api_key(cfg)
    uploader = Uploader(cfg, api_key)

    uploader.register(cfg)
    print(f"[watcher] initial scan of {len(cfg['watch_paths'])} folder(s)...")
    initial_scan(cfg, uploader)

    pending: dict = {}
    lock = threading.Lock()
    stop = threading.Event()

    handler = DebounceHandler(pending, lock, cfg["extensions"])
    observer = Observer()
    watched = 0
    for path in cfg["watch_paths"]:
        if os.path.isdir(path):
            observer.schedule(handler, path, recursive=cfg["recursive"])
            watched += 1
    observer.start()

    worker = threading.Thread(target=debounce_worker, args=(pending, lock, uploader, stop), daemon=True)
    worker.start()

    print(f"[watcher] watching {watched} folder(s). Ctrl-C to stop.")
    try:
        while True:
            time.sleep(HEARTBEAT_SECONDS)
            uploader.heartbeat()
    except KeyboardInterrupt:
        print("\n[watcher] stopping...")
    finally:
        stop.set()
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
