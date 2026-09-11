"""
Scheduler Daemon.

Lightweight timer that checks for due scheduled tasks every minute.
Instead of running its own agent, it sends prompts to the Telegram bot
by injecting messages via the Telegram Bot API. This way scheduled tasks
get full tool access through the already-running bot.

Usage:
    python scheduler.py
"""

import json
import asyncio
import sys, os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "data", "scheduled_tasks.json")

# How late a missed run may still be executed when the daemon catches up
# (e.g. the laptop was asleep at the scheduled minute and woke later). Beyond
# this window a missed run is acknowledged but skipped, so we don't fire a
# stale "morning" routine in the afternoon. Override via config if desired.
CATCHUP_GRACE = timedelta(hours=getattr(config, "SCHEDULER_CATCHUP_HOURS", 3))


def load_tasks() -> list[dict]:
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r") as f:
        return json.load(f)


def save_tasks(tasks: list[dict]):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def is_one_time_schedule(schedule: str) -> bool:
    """Check if a cron schedule can only fire once (all time/date fields are fixed)."""
    parts = schedule.strip().split()
    if len(parts) != 5:
        return False
    minute, hour, day, month, _ = parts
    # If minute, hour, day, and month are all plain integers, it's one-time
    for field in (minute, hour, day, month):
        if not field.isdigit():
            return False
    return True


def cron_matches(schedule: str, now: datetime) -> bool:
    """
    Check if a cron schedule matches the current time.
    Format: "minute hour day_of_month month day_of_week"
    """
    parts = schedule.strip().split()
    if len(parts) != 5:
        return False

    # Cron uses 0=Sunday, Python uses 0=Monday. Convert.
    cron_dow = (now.weekday() + 1) % 7

    fields = [
        (now.minute, 0, 59),
        (now.hour, 0, 23),
        (now.day, 1, 31),
        (now.month, 1, 12),
        (cron_dow, 0, 6),
    ]

    for part, (current, min_val, max_val) in zip(parts, fields):
        if not _field_matches(part, current, min_val, max_val):
            return False

    return True


def previous_fire(schedule: str, now: datetime, lookback_minutes: int = 8 * 24 * 60) -> datetime | None:
    """Most recent minute at-or-before `now` that matches the cron schedule.

    Used for catch-up: instead of only firing when the daemon happens to be
    ticking during the exact matching minute (which is missed whenever the
    machine is asleep or the daemon restarts), we find the last scheduled
    occurrence and compare it against the task's last_run.
    """
    candidate = now.replace(second=0, microsecond=0)
    for _ in range(lookback_minutes + 1):
        if cron_matches(schedule, candidate):
            return candidate
        candidate -= timedelta(minutes=1)
    return None


def _field_matches(field: str, value: int, min_val: int, max_val: int) -> bool:
    if field == "*":
        return True

    for item in field.split(","):
        if "/" in item:
            base, step = item.split("/", 1)
            step = int(step)
            if base == "*":
                if value % step == 0:
                    return True
            elif "-" in base:
                start, end = map(int, base.split("-", 1))
                if start <= value <= end and (value - start) % step == 0:
                    return True
        elif "-" in item:
            start, end = map(int, item.split("-", 1))
            if start <= value <= end:
                return True
        else:
            if int(item) == value:
                return True

    return False


_ANNOUNCE_SYSTEM = (
    "You write a single short spoken notification. Follow the instruction using ONLY "
    "the context given. Respond with just the words to be spoken — no preamble, no "
    "meta-commentary, no markdown."
)


async def _announce(prompt: str) -> str:
    """
    Run a tools-free task as one isolated LLM call.

    A task that only has to phrase something it was already handed does not need
    the agent: booting an AgentCore drags every MCP server's tool schema and the
    memory injection into context, which measured 22k-92k input tokens to produce
    two sentences. This path is the same call without any of that.

    The clock is injected because the prompt was written when the task was
    scheduled, and a heads-up that fires late must not say "start getting ready"
    for something already underway.
    """
    import workflow_runner

    adapter = workflow_runner._make_adapter()
    now = datetime.now()
    text = f"Current time: {now:%A %Y-%m-%d %-I:%M %p}\n\n{prompt}"
    resp = await adapter.chat(_ANNOUNCE_SYSTEM, [{"role": "user", "content": text}], None)
    return (resp.text or "").strip()


async def send_to_bot(prompt: str, task_name: str, sinks: list[str] | None = None,
                      use_tools: bool = True):
    """
    Run a scheduled task's prompt and deliver the result to the task's sinks
    (voice / telegram / silent — see delivery.py).

    use_tools=False runs it as a plain LLM call instead of a full agent — for
    tasks that only phrase something, which is most announcements.
    """
    import delivery

    sinks = sinks or ["telegram"]

    if not use_tools:
        try:
            response = await _announce(prompt)
            print(f"  [scheduler] Announced: {response[:80]}")
            await delivery.deliver(sinks, response)
        except Exception as e:
            print(f"  [scheduler] Announcement '{task_name}' failed: {e}")
            await delivery.deliver([s for s in sinks if s != "silent"],
                                   f"⚠️ Task '{task_name}' failed: {e}")
        return

    # Pre-run notice only makes sense on a chat channel — a spoken
    # "running scheduled task" right before the spoken result is just noise.
    if "telegram" in sinks:
        await delivery.send_telegram(f"🔔 Running scheduled task: {task_name}")

    # Run the agent core directly WITH tools enabled, but remote_tools: no MCP
    # servers are spawned per task — every tool call proxies to the dashboard's
    # single running set over the toolbus API. This also makes per-task agent
    # startup near-instant (no subprocess fleet to boot and tear down).
    # Import here to avoid circular imports at module level.
    from agent.core import AgentCore
    from memory.conversation import ConversationMemory

    # Scheduler uses its own session so it doesn't load Telegram context
    agent = AgentCore(
        enable_tools=True,
        remote_tools=True,
        session_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "data", "session_scheduler.json"),
    )
    await agent.start()

    try:
        response = await agent.process(prompt, source="scheduler")
        print(f"  [scheduler] Response: {response[:100]}...")

        # Inject a summary into the Telegram session so the user can ask about it
        if "telegram" in sinks:
            try:
                telegram_conv = ConversationMemory()  # loads default session.json
                summary = response[:500] if len(response) > 500 else response
                telegram_conv.add_message(
                    "assistant",
                    f"[Scheduled task '{task_name}' ran at {datetime.now().strftime('%I:%M %p')}]\n"
                    f"Prompt: {prompt[:200]}\n"
                    f"Result: {summary}",
                )
                telegram_conv.save_session()
            except Exception as e2:
                print(f"  [scheduler] Failed to inject into Telegram session: {e2}")

        await delivery.deliver(sinks, response)
    except Exception as e:
        print(f"  [scheduler] Task failed: {e}")
        await delivery.deliver(
            [s for s in sinks if s != "silent"],
            f"⚠️ Task '{task_name}' failed: {e}",
        )
    finally:
        try:
            await agent.shutdown()
        except (Exception, BaseException):
            pass


async def run_task(task: dict):
    """Execute a scheduled task.

    The agent run is isolated inside its own asyncio.Task. Tearing down the
    MCP servers (anyio/stdio_client) leaks a CancelledError onto whatever task
    is running its cleanup; running it in a child task means that stray cancel
    lands on the (already-finishing) child instead of the daemon's main loop.
    Without this, the daemon dies on the next `await` after every task.
    """
    print(f"  [scheduler] Running task: {task['name']}")
    print(f"  [scheduler] Prompt: {task['prompt'][:80]}")
    try:
        await asyncio.create_task(
            send_to_bot(task["prompt"], task["name"], task.get("sinks") or ["telegram"],
                        use_tools=task.get("tools", True)))
    except asyncio.CancelledError:
        # Spurious cancellation leaked from MCP teardown — the task itself
        # already ran. Swallow it so the daemon keeps running. (A real
        # shutdown arrives as KeyboardInterrupt at the main loop, not here.)
        print(f"  [scheduler] Absorbed stray cancellation after task '{task['name']}'")
    except Exception as e:
        print(f"  [scheduler] Task '{task['name']}' raised {type(e).__name__}: {e} — daemon continuing")


async def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║       🧠 Second Brain — Scheduler Daemon        ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    print("  Scheduler running. Checking tasks every 60 seconds.")
    print()

    try:
        while True:
            now = datetime.now().replace(second=0, microsecond=0)
            tasks = load_tasks()

            for task in tasks:
                if not task.get("enabled", True):
                    continue

                # Find the most recent scheduled occurrence at-or-before now.
                fire = previous_fire(task["schedule"], now)
                if fire is None:
                    continue

                # Skip if we've already run this occurrence (or a later one).
                last_run = task.get("last_run")
                if last_run:
                    last_run_dt = datetime.fromisoformat(last_run).replace(second=0, microsecond=0)
                    if last_run_dt >= fire:
                        continue

                # Catch-up grace: if the missed occurrence is too old (machine
                # was off all day, etc.), acknowledge it but don't run a stale
                # routine. Marking last_run stops us re-checking every tick.
                if now - fire > CATCHUP_GRACE:
                    task["last_run"] = fire.isoformat()
                    save_tasks(tasks)
                    print(f"  [scheduler] Skipped stale run of '{task['name']}' "
                          f"(due {fire:%Y-%m-%d %H:%M}, beyond {CATCHUP_GRACE} grace)")
                    continue

                # Run the task. Guard the whole block so no task failure can
                # ever take down the daemon — it must survive to the next tick.
                try:
                    late = now - fire
                    if late > timedelta(minutes=1):
                        print(f"  [scheduler] Catch-up: '{task['name']}' was due {fire:%H:%M}, "
                              f"running {int(late.total_seconds() // 60)} min late")
                    await run_task(task)

                    # Auto-delete one-time schedules, otherwise record the
                    # occurrence we just satisfied.
                    if is_one_time_schedule(task["schedule"]):
                        tasks = [t for t in tasks if t["id"] != task["id"]]
                        print(f"  [scheduler] Auto-deleted one-time task: {task['name']}")
                    else:
                        task["last_run"] = fire.isoformat()
                    save_tasks(tasks)
                except (Exception, asyncio.CancelledError) as e:
                    print(f"  [scheduler] Error handling task '{task.get('name')}': {type(e).__name__}: {e}")

            await asyncio.sleep(60)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n  Shutting down scheduler...")
        print("  Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
