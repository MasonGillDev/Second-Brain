"""
Trigger Store.

CRUD for trigger definitions, persisted as JSON at config.TRIGGERS_FILE.
This module only stores and validates definitions; it never fires them (see
trigger_engine.py for the runtime).

A trigger is an event-driven automation: source → filter → action → sinks.

    {
      "name": "arrived_home",
      "description": "iOS Shortcut posts when I arrive home.",
      "source": {"type": "webhook", "secret": "<auto-minted hex>"},
      "filter": "{{payload.event}} == arrived_home",        # optional
      "action": {"type": "workflow", "workflow": "evening_arrival",
                 "args": {"who": "{{payload.person}}"}},
      "sinks": ["voice", "telegram"],                        # default ["telegram"]
      "enabled": true,
      "debounce_seconds": 300,                               # default 0
      "created_at": "..."
    }

Source types:
  - webhook: fired by POST /hooks/<name> on the dashboard (per-trigger secret).
  - poll:    the engine fetches on an interval and fires on change/condition:
             {"type": "poll", "interval_seconds": 300,
              "watch": {"url": "..."} | {"tool": "server__tool", "args": {...}},
              "fire_on": "change" | "condition", "condition": "{{output}} contains X"}

Action types:
  - workflow: run a saved workflow (workflow_runner), payload interpolated into args.
  - prompt:   run an agent prompt with full tools ({{payload...}} interpolated).

Every trigger gets a secret — poll triggers too, so /hooks/<name> doubles as a
uniform manual test-fire path for both source types.
"""

import json
import os
import re
import secrets as _secrets
from datetime import datetime

import config

_NAME_RE = re.compile(r"^[a-z0-9_]{1,40}$")

SOURCE_TYPES = {"webhook", "poll"}
ACTION_TYPES = {"workflow", "prompt"}
FIRE_ON = {"change", "condition"}
MIN_POLL_INTERVAL = 30


def _path() -> str:
    return config.TRIGGERS_FILE


def load_triggers() -> list[dict]:
    path = _path()
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def save_triggers(triggers: list[dict]):
    """Atomic write (tmp + rename) — the dashboard and the triggers MCP server
    are separate processes; a torn write must never corrupt the registry."""
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(triggers, f, indent=2)
    os.replace(tmp, path)


def get_trigger(name: str) -> dict | None:
    for t in load_triggers():
        if t.get("name") == name:
            return t
    return None


def webhook_url(name: str) -> str:
    return f"{config.PUBLIC_BASE_URL}/hooks/{name}"


def validate_trigger(defn: dict) -> list[str]:
    """Return a list of human-readable problems ([] == valid)."""
    if not isinstance(defn, dict):
        return ["definition must be a JSON object"]

    errs: list[str] = []
    if not _NAME_RE.match(defn.get("name") or ""):
        errs.append("name must be snake_case, 1-40 chars of [a-z0-9_]")
    if not defn.get("description"):
        errs.append("description is required (one line: what fires it / what it does)")

    src = defn.get("source")
    if not isinstance(src, dict) or src.get("type") not in SOURCE_TYPES:
        errs.append(f"source.type must be one of {sorted(SOURCE_TYPES)}")
    elif src["type"] == "poll":
        interval = src.get("interval_seconds")
        if not isinstance(interval, int) or interval < MIN_POLL_INTERVAL:
            errs.append(f"poll source needs interval_seconds >= {MIN_POLL_INTERVAL}")
        watch = src.get("watch")
        if not isinstance(watch, dict) or len({"url", "tool"} & set(watch)) != 1:
            errs.append("poll source needs watch with exactly one of 'url' or 'tool'")
        elif "tool" in watch and "__" not in (watch.get("tool") or ""):
            errs.append("watch.tool must be a namespaced name like 'calendar__get_day'")
        fire_on = src.get("fire_on", "change")
        if fire_on not in FIRE_ON:
            errs.append(f"fire_on must be one of {sorted(FIRE_ON)}")
        if fire_on == "condition" and not src.get("condition"):
            errs.append("fire_on 'condition' requires a condition string")

    act = defn.get("action")
    if not isinstance(act, dict) or act.get("type") not in ACTION_TYPES:
        errs.append(f"action.type must be one of {sorted(ACTION_TYPES)}")
    elif act["type"] == "workflow":
        wf = act.get("workflow")
        if not wf:
            errs.append("workflow action needs a 'workflow' name")
        else:
            import workflow_store
            if not workflow_store.get_workflow(wf):
                errs.append(f"no workflow named '{wf}' exists")
    elif act["type"] == "prompt" and not (act.get("prompt") or "").strip():
        errs.append("prompt action needs a non-empty 'prompt'")

    from delivery import VALID_SINKS
    sinks = defn.get("sinks")
    if sinks is not None and (not isinstance(sinks, list) or not set(sinks) <= VALID_SINKS):
        errs.append(f"sinks must be a list drawn from {sorted(VALID_SINKS)}")

    if "filter" in defn and not isinstance(defn.get("filter"), str):
        errs.append("filter must be a condition string")

    debounce = defn.get("debounce_seconds", 0)
    if not isinstance(debounce, int) or debounce < 0:
        errs.append("debounce_seconds must be a non-negative integer")

    return errs


def upsert_trigger(defn: dict, *, overwrite: bool = True) -> str:
    """Create or replace a trigger. Returns 'created' or 'updated'. Raises
    ValueError with a joined message if the definition is invalid.

    A missing source.secret is auto-minted; an update that omits the secret
    keeps the existing one (so saved webhook URLs don't break on edit)."""
    errs = validate_trigger(defn)
    if errs:
        raise ValueError("; ".join(errs))

    defn.setdefault("sinks", ["telegram"])
    defn.setdefault("enabled", True)
    defn.setdefault("debounce_seconds", 0)
    defn.setdefault("created_at", datetime.now().isoformat())

    triggers = load_triggers()
    action = "created"
    for i, t in enumerate(triggers):
        if t.get("name") == defn["name"]:
            if not overwrite:
                raise ValueError(f"trigger '{defn['name']}' already exists")
            if not defn["source"].get("secret"):
                defn["source"]["secret"] = (t.get("source") or {}).get("secret") or _secrets.token_hex(16)
            triggers[i] = defn
            action = "updated"
            break
    else:
        if not defn["source"].get("secret"):
            defn["source"]["secret"] = _secrets.token_hex(16)
        triggers.append(defn)
    save_triggers(triggers)
    return action


def delete_trigger(name: str) -> bool:
    triggers = load_triggers()
    remaining = [t for t in triggers if t.get("name") != name]
    if len(remaining) == len(triggers):
        return False
    save_triggers(remaining)
    return True


def set_enabled(name: str, enabled: bool) -> bool:
    triggers = load_triggers()
    for t in triggers:
        if t.get("name") == name:
            t["enabled"] = bool(enabled)
            save_triggers(triggers)
            return True
    return False
