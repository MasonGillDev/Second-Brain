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
import os
from datetime import datetime

import config

TASKS_FILE = "./memory/data/scheduled_tasks.json"


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


async def send_to_bot(prompt: str, task_name: str):
    """
    Send a message to the Telegram bot as if the user sent it.
    The bot processes it with full tool access and replies.
    """
    import httpx

    from keychain import get_secret
    try:
        token = get_secret("telegram-bot-token")
    except RuntimeError:
        token = None
    user_id = config.TELEGRAM_NOTIFY_USER_ID

    if not token or not user_id:
        print("  [scheduler] Missing telegram-bot-token in Keychain or TELEGRAM_NOTIFY_USER_ID")
        return

    # First, notify the user that a scheduled task is running
    notify_url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(notify_url, json={
            "chat_id": user_id,
            "text": f"🔔 Running scheduled task: {task_name}",
        })

    # Now send the actual prompt as a message to the bot.
    # We use the bot's /sendMessage to simulate the task,
    # but the bot needs to process it. We'll use a special prefix
    # so the bot knows it's a scheduled task.
    #
    # Since we can't inject messages into the bot's handler directly
    # via the Telegram API, we send the prompt as a regular message
    # from the bot to the user, then the user's bot processes it.
    #
    # Actually, the cleanest approach: use the Telegram Bot API's
    # getUpdates won't work. Instead, we call the agent core directly
    # but WITH tools enabled, since the Telegram bot's MCP servers
    # are separate processes that can handle concurrent connections.

    # Import here to avoid circular imports at module level
    from core import AgentCore
    from memory.conversation import ConversationMemory

    # Scheduler uses its own session so it doesn't load Telegram context
    agent = AgentCore(
        enable_tools=True,
        session_file="./memory/data/session_scheduler.json",
    )
    await agent.start()

    try:
        response = await agent.process(prompt)
        print(f"  [scheduler] Response: {response[:100]}...")

        # Inject a summary into the Telegram session so the user can ask about it
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

        # Send the response to Telegram
        chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
        async with httpx.AsyncClient() as client:
            for chunk in chunks:
                await client.post(notify_url, json={
                    "chat_id": user_id,
                    "text": chunk,
                })
    except Exception as e:
        print(f"  [scheduler] Task failed: {e}")
        async with httpx.AsyncClient() as client:
            await client.post(notify_url, json={
                "chat_id": user_id,
                "text": f"⚠️ Task '{task_name}' failed: {e}",
            })
    finally:
        try:
            await agent.shutdown()
        except (Exception, BaseException):
            pass


async def run_task(task: dict):
    """Execute a scheduled task."""
    print(f"  [scheduler] Running task: {task['name']}")
    print(f"  [scheduler] Prompt: {task['prompt'][:80]}")
    await send_to_bot(task["prompt"], task["name"])


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

                if not cron_matches(task["schedule"], now):
                    continue

                # Prevent running the same task twice in the same minute
                last_run = task.get("last_run")
                if last_run:
                    last_run_dt = datetime.fromisoformat(last_run).replace(second=0, microsecond=0)
                    if last_run_dt == now:
                        continue

                # Run the task
                await run_task(task)

                # Auto-delete one-time schedules, otherwise update last_run
                if is_one_time_schedule(task["schedule"]):
                    tasks = [t for t in tasks if t["id"] != task["id"]]
                    print(f"  [scheduler] Auto-deleted one-time task: {task['name']}")
                else:
                    task["last_run"] = now.isoformat()
                save_tasks(tasks)

            await asyncio.sleep(60)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n  Shutting down scheduler...")
        print("  Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
