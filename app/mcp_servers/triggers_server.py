"""
Triggers MCP Server.

The agent's interface to the trigger registry: event-driven automations that
fire in response to webhooks or polled changes, run a workflow or agent prompt,
and deliver results to voice/telegram. Definitions live in trigger_store; the
runtime is trigger_engine, which runs inside the dashboard process (webhook
routes + poll loop) — this server only manages definitions and history.

test_fire_trigger crosses processes: it POSTs to the dashboard's /hooks/<name>
endpoint, because the engine (debounce state, poll baselines, running agent)
lives there, not here.
"""

import sys
import os
import json
from datetime import datetime

# Add project root (app/) to path so we can import the shared modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

import config
import db
import trigger_store as store

mcp = FastMCP("triggers")

_LOCAL_BASE = "http://127.0.0.1:5001"


def _usage_block(t: dict) -> str:
    """How to call a webhook trigger — shown after create/get so the user can
    wire up an iOS Shortcut (or curl) without asking again."""
    if (t.get("source") or {}).get("type") != "webhook":
        return ""
    secret = t["source"].get("secret", "")
    return (
        f"\nWebhook URL: {store.webhook_url(t['name'])}"
        f"\nAuth: header 'X-Hook-Secret: {secret}'  (or ?secret={secret})"
        f"\nPOST a JSON body; its fields are available as {{{{payload.field}}}} "
        f"in the trigger's filter and action."
        f"\niOS Shortcut: 'Get Contents of URL' -> Method POST, Request Body JSON, "
        f"add the header above. Requires Tailscale connected on the phone."
    )


@mcp.tool()
def create_trigger(definition: str) -> str:
    """
    Create or update an event trigger from a JSON definition.

    A trigger fires in response to an event (webhook call or polled change),
    optionally filters on the event payload, runs an action, and delivers the
    result to sinks. `definition` is a JSON object:

      {
        "name": "arrived_home",
        "description": "One line: what fires it and what it does.",
        "source": {"type": "webhook"},
        "filter": "{{payload.event}} == arrived_home",
        "action": {"type": "workflow", "workflow": "evening_arrival",
                   "args": {"who": "{{payload.person}}"}},
        "sinks": ["voice", "telegram"],
        "debounce_seconds": 300
      }

    Source types:
      - {"type": "webhook"} — fired by POST to /hooks/<name>. A secret is
        auto-minted; the reply includes the full URL + header for the caller
        (e.g. an iOS Shortcut personal automation).
      - {"type": "poll", "interval_seconds": 300,
         "watch": {"url": "https://..."} OR {"tool": "server__tool", "args": {...}},
         "fire_on": "change"}  — fetches on the interval, fires when the output
        changes. Or "fire_on": "condition" with "condition": "{{output}} contains X"
        — fires when the condition BECOMES true (edge-triggered).

    Action types (exactly one):
      - {"type": "workflow", "workflow": "name", "args": {...}} — deterministic,
        cheap; use when the response to the event is always the same steps.
      - {"type": "prompt", "prompt": "text with {{payload...}}"} — a full agent
        run with all tools; use when the response needs judgment.

    Sinks (where the action's result goes): "voice" (spoken aloud by the voice
    assistant), "telegram", "silent" (no delivery — the action's side effects
    are the point). Default ["telegram"].

    Filters/conditions use the workflow condition language: X == Y, X != Y,
    X contains Y, X not contains Y, X is empty, X is not empty, X > Y, X < Y.
    Webhook payload fields are referenced as {{payload.field}} (nested:
    {{payload.a.b}}); poll output as {{output}}.

    debounce_seconds suppresses repeat firings within the window (e.g. an iOS
    location automation that triggers several times as you arrive).
    """
    try:
        defn = json.loads(definition)
    except json.JSONDecodeError as e:
        return f"[ERROR] definition is not valid JSON: {e}"
    try:
        action = store.upsert_trigger(defn)
    except ValueError as e:
        return f"[ERROR] invalid trigger: {e}"
    t = store.get_trigger(defn["name"])
    return f"Trigger '{defn['name']}' {action}." + _usage_block(t)


@mcp.tool()
def list_triggers() -> str:
    """List all triggers: source type, action, sinks, enabled state, debounce."""
    triggers = store.load_triggers()
    if not triggers:
        return "No triggers defined."
    last = db.get_last_fired_map()
    lines = []
    for t in triggers:
        src = t.get("source") or {}
        act = t.get("action") or {}
        act_desc = (f"workflow '{act.get('workflow')}'" if act.get("type") == "workflow"
                    else f"prompt \"{(act.get('prompt') or '')[:60]}\"")
        state = "enabled" if t.get("enabled", True) else "DISABLED"
        fired = last.get(t["name"])
        fired_s = datetime.fromtimestamp(fired).strftime("%Y-%m-%d %H:%M") if fired else "never"
        lines.append(
            f"- {t['name']} ({src.get('type')}, {state})\n"
            f"  {t.get('description', '')}\n"
            f"  Action: {act_desc} | Sinks: {', '.join(t.get('sinks') or ['telegram'])} "
            f"| Debounce: {t.get('debounce_seconds', 0)}s | Last fired: {fired_s}"
        )
    return "\n\n".join(lines)


@mcp.tool()
def get_trigger(name: str) -> str:
    """Get a trigger's full JSON definition, plus its webhook URL and secret."""
    t = store.get_trigger(name)
    if not t:
        return f"[ERROR] no trigger named '{name}'"
    return json.dumps(t, indent=2) + _usage_block(t)


@mcp.tool()
def delete_trigger(name: str) -> str:
    """Delete a trigger by name."""
    if store.delete_trigger(name):
        return f"Deleted trigger '{name}'."
    return f"[ERROR] no trigger named '{name}'"


@mcp.tool()
def set_trigger_enabled(name: str, enabled: bool) -> str:
    """Enable or disable a trigger without deleting it."""
    if store.set_enabled(name, enabled):
        return f"Trigger '{name}' is now {'enabled' if enabled else 'disabled'}."
    return f"[ERROR] no trigger named '{name}'"


@mcp.tool()
def test_fire_trigger(name: str, payload: str = "{}") -> str:
    """
    Manually fire a trigger with a test payload (bypasses debounce).

    The action runs asynchronously in the dashboard — check
    get_trigger_firings a few seconds later for the outcome.

    Args:
        name: trigger to fire.
        payload: JSON object standing in for the webhook payload,
                 e.g. '{"event": "arrived_home"}'.
    """
    t = store.get_trigger(name)
    if not t:
        return f"[ERROR] no trigger named '{name}'"
    try:
        body = json.loads(payload or "{}")
    except json.JSONDecodeError as e:
        return f"[ERROR] payload is not valid JSON: {e}"

    import httpx
    secret = (t.get("source") or {}).get("secret", "")
    try:
        resp = httpx.post(
            f"{_LOCAL_BASE}/hooks/{name}",
            params={"test": "1"},
            headers={"X-Hook-Secret": secret},
            json=body,
            timeout=10,
        )
    except Exception as e:
        return f"[ERROR] could not reach the dashboard at {_LOCAL_BASE}: {e}"
    if resp.status_code != 200:
        return f"[ERROR] dashboard returned {resp.status_code}: {resp.text[:200]}"
    status = resp.json().get("status")
    return (f"Test fire '{name}': {status}. The action runs in the background — "
            f"call get_trigger_firings('{name}') in a few seconds for the result.")


@mcp.tool()
def get_trigger_firings(name: str = "", limit: int = 10) -> str:
    """
    Recent trigger firing history (newest first): status, payload, result.

    Args:
        name: filter to one trigger; empty = all triggers.
        limit: max rows.
    """
    rows = db.get_trigger_firings(trigger_name=name or None, limit=limit)
    if not rows:
        return "No firings recorded."
    lines = []
    for r in rows:
        ts = datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        dur = f" ({r['duration_ms'] / 1000:.1f}s)" if r["duration_ms"] is not None else ""
        line = f"[{ts}] {r['trigger_name']} <- {r['source']}: {r['status'].upper()}{dur}"
        if r.get("payload"):
            line += f"\n  payload: {r['payload'][:200]}"
        if r.get("result"):
            line += f"\n  result: {r['result'][:300]}"
        lines.append(line)
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
