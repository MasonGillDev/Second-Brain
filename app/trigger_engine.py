"""
Trigger Engine — the runtime for trigger definitions (see trigger_store.py).

Lives inside the dashboard process (the always-on service with the HTTP
server). Webhook firings arrive via dashboard/routes/hooks.py; poll sources
run in poll_loop(), a background task started at app startup. Both funnel
through accept(), which applies enabled/debounce gating and dispatches the
action in a background asyncio task so the caller (a webhook request that
must 200 fast, or the poll loop) never waits on an LLM.

Dispatch: filter (workflow_runner's `when` condition language over the
flattened payload) → action (workflow via the dashboard agent's own MCP
clients, or an agent prompt in a fresh isolated AgentCore) → sinks
(delivery.py) → a row in the trigger_firings table.

Tool access ALWAYS goes through RouterBroker(agent.router) — never a fresh
ToolBroker. A second fleet of MCP subprocesses can deadlock on shared OS
resources (the Cync token lock), which is the same reason AgentCore runs
workflows in-process.
"""

import asyncio
import hashlib
import json
import os
import time

import config
import db
import delivery
import trigger_store
import workflow_runner
from workflow_runner import RouterBroker, WorkflowError

# Session file for prompt-action AgentCores — must be distinct from the
# dashboard/scheduler/telegram sessions (AgentCore's locks are per-instance
# and do not protect a shared session file across instances).
_TRIGGER_SESSION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "memory", "data", "session_triggers.json")


def flatten_payload(payload: dict, root: str = "payload") -> dict[str, str]:
    """Flatten a JSON payload into dotted variable names for interpolation:

        {"event": "x", "loc": {"lat": 1}} ->
        {"payload": '{"event"...}', "payload.event": "x",
         "payload.loc": '{"lat": 1}', "payload.loc.lat": "1"}

    Every node (including dict/list branches, as JSON) gets an entry, so both
    {{payload}} and {{payload.loc.lat}} work. Leaf normalization matches the
    workflow variable conventions (bools -> 'true'/'false', None -> '')."""
    flat: dict[str, str] = {}

    def visit(value, key: str):
        if isinstance(value, dict):
            flat[key] = json.dumps(value, ensure_ascii=False)
            for k, v in value.items():
                visit(v, f"{key}.{k}")
        elif isinstance(value, list):
            flat[key] = json.dumps(value, ensure_ascii=False)
            for i, v in enumerate(value):
                visit(v, f"{key}.{i}")
        elif isinstance(value, bool):
            flat[key] = "true" if value else "false"
        elif value is None:
            flat[key] = ""
        else:
            flat[key] = str(value)

    visit(payload or {}, root)
    return flat


class TriggerEngine:
    def __init__(self, agent):
        self._agent = agent  # the dashboard's long-lived AgentCore (for its router)
        # Debounce state, seeded from history so a restart can't defeat a window.
        self._last_fired: dict[str, float] = db.get_last_fired_map()
        # Strong refs to in-flight dispatch tasks (asyncio only keeps weak ones).
        self._tasks: set[asyncio.Task] = set()
        # At most ONE prompt-action AgentCore at a time: each spawns its own MCP
        # subprocess fleet, and two fleets can deadlock on the Cync token lock.
        # (A trigger racing the separate scheduler daemon's AgentCore remains
        # possible — that's the same pre-existing race the scheduler already
        # has with the dashboard agent, accepted for now.)
        self._prompt_lock = asyncio.Lock()
        # Poll runtime state per trigger name.
        self._poll_state: dict[str, dict] = {}

    # ---- ingestion ---------------------------------------------------------

    def accept(self, trigger: dict, payload: dict, source: str) -> str:
        """Gate a firing and hand it to a background dispatch task.

        Synchronous on purpose: no awaits between the filter/debounce checks
        and the stamp, so concurrent webhooks can't slip through the window
        together. The filter runs BEFORE the debounce stamp — an event that
        doesn't match must not suppress a matching one right behind it.
        Returns 'accepted' | 'filtered' | 'debounced' | 'disabled' | 'error'."""
        name = trigger["name"]
        if not trigger.get("enabled", True):
            return "disabled"

        payload_snapshot = json.dumps(payload, ensure_ascii=False)[:2000]
        try:
            variables = workflow_runner._builtins() | flatten_payload(payload)
            flt = trigger.get("filter")
            if flt and not workflow_runner._eval_when(flt, variables):
                db.log_trigger_firing(name, source, "filtered", payload=payload_snapshot)
                return "filtered"
        except Exception as e:
            # A broken filter expression is an authoring error — surface it.
            db.log_trigger_firing(name, source, "error",
                                  payload=payload_snapshot, result=f"filter: {e}")
            return "error"

        now = time.time()
        debounce = trigger.get("debounce_seconds", 0) or 0
        if source != "test" and debounce and now - self._last_fired.get(name, 0) < debounce:
            db.log_trigger_firing(name, source, "debounced")
            return "debounced"
        # Stamp at accept time so a burst dedupes even while a dispatch runs.
        self._last_fired[name] = now

        task = asyncio.create_task(self._dispatch(trigger, payload, variables, source))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return "accepted"

    # ---- dispatch ----------------------------------------------------------

    async def _dispatch(self, trigger: dict, payload: dict, variables: dict, source: str):
        """Action → sinks → history row (filter already passed in accept()).
        Absorbs every exception — including stray CancelledError leaked by MCP
        client teardown (see scheduler.run_task) — so nothing propagates into
        the dashboard loop."""
        name = trigger["name"]
        started = time.time()
        payload_snapshot = json.dumps(payload, ensure_ascii=False)[:2000]
        try:
            print(f"  [trigger] Firing '{name}' ({source})")
            result = await self._run_action(trigger, variables)

            await delivery.deliver(trigger.get("sinks") or ["telegram"], result)
            db.log_trigger_firing(
                name, source, "fired", payload=payload_snapshot, result=result,
                duration_ms=int((time.time() - started) * 1000))
            print(f"  [trigger] '{name}' done in {time.time() - started:.1f}s")
        except (Exception, asyncio.CancelledError) as e:
            err = f"{type(e).__name__}: {e}"
            print(f"  [trigger] '{name}' failed: {err}")
            db.log_trigger_firing(
                name, source, "error", payload=payload_snapshot, result=err,
                duration_ms=int((time.time() - started) * 1000))
            try:
                sinks = [s for s in (trigger.get("sinks") or ["telegram"]) if s != "silent"]
                await delivery.deliver(sinks, f"⚠️ Trigger '{name}' failed: {err}")
            except Exception:
                pass

    async def _run_action(self, trigger: dict, variables: dict) -> str:
        act = trigger["action"]
        if act["type"] == "workflow":
            args = workflow_runner._interp_value(act.get("args") or {}, variables)
            return await workflow_runner.run_workflow(
                act["workflow"], args, broker=RouterBroker(self._agent.router))

        # prompt action: fresh isolated AgentCore, scheduler-style.
        # The run is isolated in a child task with its result captured in a
        # holder: MCP client teardown (anyio) can leak a cancellation onto the
        # awaiting task AFTER process() already finished (see scheduler.run_task)
        # — the holder lets us keep the finished result even when that happens.
        text = workflow_runner._interp(act["prompt"], variables)
        async with self._prompt_lock:
            holder: dict = {}

            async def _run():
                from agent.core import AgentCore
                # Borrow the dashboard agent's already-running router: spawning
                # a fresh MCP fleet here would put a second light/music/tv
                # server inside this very process, competing with the
                # dashboard's own (the Cync cloud evicts one of the sessions).
                agent = AgentCore(enable_tools=True, session_file=_TRIGGER_SESSION,
                                  router=self._agent.router)
                await agent.start()
                try:
                    holder["result"] = await agent.process(text, source="trigger")
                finally:
                    try:
                        await agent.shutdown()
                    except (Exception, BaseException):
                        pass  # teardown noise — the run itself already finished

            try:
                await asyncio.create_task(_run())
            except asyncio.CancelledError:
                if "result" not in holder:
                    raise  # genuine cancellation (app shutdown/reload) mid-run
                # Stray teardown cancel after the run finished — absorb it.
            return holder["result"]

    # ---- poll sources ------------------------------------------------------

    async def poll_loop(self):
        """Drive all poll-source triggers. Reloads the registry every tick so
        edits apply without a restart. The loop body is fully guarded — it must
        survive to the next tick no matter what a fetch or dispatch does."""
        print(f"  [trigger] Poll loop started (tick {config.TRIGGER_POLL_TICK_SECONDS}s)")
        while True:
            try:
                now = time.time()
                triggers = trigger_store.load_triggers()
                poll_names = set()
                for trig in triggers:
                    if trig.get("source", {}).get("type") != "poll":
                        continue
                    poll_names.add(trig["name"])
                    if not trig.get("enabled", True):
                        continue
                    state = self._poll_state.setdefault(
                        trig["name"], {"next_due": 0.0, "last_hash": None,
                                       "last_cond": None, "running": False})
                    if now < state["next_due"] or state["running"]:
                        continue
                    state["next_due"] = now + trig["source"].get("interval_seconds", 300)
                    state["running"] = True
                    task = asyncio.create_task(self._poll_once(trig, state))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
                # Forget state for deleted triggers.
                for stale in set(self._poll_state) - poll_names:
                    del self._poll_state[stale]
            except Exception as e:
                print(f"  [trigger] poll loop error: {type(e).__name__}: {e}")
            await asyncio.sleep(config.TRIGGER_POLL_TICK_SECONDS)

    async def _poll_once(self, trigger: dict, state: dict):
        """One fetch + change/condition evaluation for a poll trigger."""
        name = trigger["name"]
        try:
            output = await self._fetch(trigger["source"]["watch"])

            fire = False
            if trigger["source"].get("fire_on", "change") == "condition":
                variables = (workflow_runner._builtins()
                             | flatten_payload({"output": output}, root="payload")
                             | {"output": output})
                cond = workflow_runner._eval_when(trigger["source"]["condition"], variables)
                # Edge-triggered: fire on the False->True transition only, so a
                # persistently-true condition doesn't fire every interval.
                fire = cond and not state["last_cond"]
                state["last_cond"] = cond
            else:
                h = hashlib.sha256(output.encode()).hexdigest()
                # First observation after startup just baselines — restarting
                # the dashboard must not fire every watcher.
                fire = state["last_hash"] is not None and h != state["last_hash"]
                state["last_hash"] = h

            if fire:
                self.accept(trigger, {"output": output[:4000], "changed": True}, source="poll")
        except (Exception, asyncio.CancelledError) as e:
            # Fetch errors don't fire and don't clobber baselines.
            print(f"  [trigger] poll '{name}' fetch failed: {type(e).__name__}: {e}")
        finally:
            state["running"] = False

    async def _fetch(self, watch: dict) -> str:
        if "url" in watch:
            import httpx
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(watch["url"])
                return resp.text
        args = workflow_runner._interp_value(watch.get("args") or {}, workflow_runner._builtins())
        out = await RouterBroker(self._agent.router).call(watch["tool"], args)
        return out if isinstance(out, str) else str(out)
