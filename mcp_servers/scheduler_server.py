"""
Scheduler MCP Server.

Manages scheduled tasks stored in a JSON file.
The separate scheduler.py daemon reads this file and executes due tasks.
"""

import json
import os
import uuid
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("scheduler")

TASKS_FILE = "./memory/data/scheduled_tasks.json"


def _load_tasks() -> list[dict]:
    """Load tasks from disk."""
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r") as f:
        return json.load(f)


def _save_tasks(tasks: list[dict]):
    """Save tasks to disk."""
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


@mcp.tool()
def create_scheduled_task(
    name: str,
    prompt: str,
    schedule: str,
    notify_telegram: bool = True,
) -> str:
    """
    Create a new scheduled task.

    Args:
        name: Short name for the task (e.g., "morning_news").
        prompt: The message to send to the agent when this task runs.
               This is what the agent will process and respond to.
               Example: "Give me a summary of today's top news headlines"
        schedule: Cron-style schedule string. Format: "minute hour day_of_month month day_of_week"
               Examples:
                 "0 8 * * *"    = every day at 8:00 AM
                 "0 8 * * 1-5"  = weekdays at 8:00 AM
                 "30 9 * * 1"   = Mondays at 9:30 AM
                 "0 */2 * * *"  = every 2 hours
                 "0 8,18 * * *" = 8:00 AM and 6:00 PM daily
        notify_telegram: If true, send the result to Telegram (default true).
    """
    tasks = _load_tasks()

    # Check for duplicate name
    for t in tasks:
        if t["name"] == name:
            return f"Task '{name}' already exists. Delete it first or use a different name."

    task = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "prompt": prompt,
        "schedule": schedule,
        "notify_telegram": notify_telegram,
        "enabled": True,
        "created_at": datetime.now().isoformat(),
        "last_run": None,
    }

    tasks.append(task)
    _save_tasks(tasks)

    return f"Created scheduled task '{name}' (id: {task['id']})\nSchedule: {schedule}\nPrompt: {prompt}"


@mcp.tool()
def list_scheduled_tasks() -> str:
    """List all scheduled tasks."""
    tasks = _load_tasks()

    if not tasks:
        return "No scheduled tasks."

    lines = []
    for t in tasks:
        status = "enabled" if t["enabled"] else "disabled"
        last = t["last_run"] or "never"
        lines.append(
            f"- [{t['id']}] {t['name']} ({status})\n"
            f"  Schedule: {t['schedule']}\n"
            f"  Prompt: {t['prompt'][:80]}\n"
            f"  Last run: {last}"
        )

    return "\n\n".join(lines)


@mcp.tool()
def delete_scheduled_task(name: str) -> str:
    """
    Delete a scheduled task by name or ID.

    Args:
        name: The name or ID of the task to delete.
    """
    tasks = _load_tasks()
    original_count = len(tasks)

    tasks = [t for t in tasks if t["name"] != name and t["id"] != name]

    if len(tasks) == original_count:
        return f"No task found with name or ID '{name}'."

    _save_tasks(tasks)
    return f"Deleted task '{name}'."


@mcp.tool()
def toggle_scheduled_task(name: str) -> str:
    """
    Enable or disable a scheduled task by name or ID.

    Args:
        name: The name or ID of the task to toggle.
    """
    tasks = _load_tasks()

    for t in tasks:
        if t["name"] == name or t["id"] == name:
            t["enabled"] = not t["enabled"]
            _save_tasks(tasks)
            status = "enabled" if t["enabled"] else "disabled"
            return f"Task '{t['name']}' is now {status}."

    return f"No task found with name or ID '{name}'."


if __name__ == "__main__":
    mcp.run(transport="stdio")
