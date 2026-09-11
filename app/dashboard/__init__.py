"""
Second Brain Dashboard — Quart app factory.
"""

import os
import sys
import io
import re
import time
import asyncio
import logging
import collections
from quart import Quart

from agent.core import AgentCore
from memory.vector_store import VectorStore
from keychain import get_secret
import config
import db


# Pattern to extract [tag] from log lines
_TAG_RE = re.compile(r'\[(\w+)\]')


class LogCapture(io.TextIOBase):
    """Tee stdout to both console, an in-memory ring buffer, and SQLite."""

    def __init__(self, original, buffer, subscribers):
        self.original = original
        self.buffer = buffer
        self.subscribers = subscribers

    # Endpoints to exclude from log capture (prevent feedback loops + sub-dashboard noise)
    _SKIP_PATTERNS = ("/api/logs", "/api/costs", "/api/lights", "/d/")

    # Path segment identifying sub-dashboard code (used for stack-frame check)
    _SUB_DASHBOARD_PATH = os.sep + os.path.join("clients", "dashboards") + os.sep

    def write(self, text):
        self.original.write(text)
        if text.strip():
            msg = text.strip()

            # Skip logging requests to our own polling endpoints + sub-dashboard URLs
            if any(p in msg for p in self._SKIP_PATTERNS):
                return len(text)

            # Skip prints originating from sub-dashboard code (clients/dashboards/*)
            if self._called_from_sub_dashboard():
                return len(text)

            entry = {"ts": time.time(), "text": msg}
            self.buffer.append(entry)

            # Persist to SQLite
            level, source = self._classify(msg)
            try:
                db.log_message(level, source, msg)
            except Exception:
                pass  # don't break stdout on db errors
        return len(text)

    @classmethod
    def _called_from_sub_dashboard(cls) -> bool:
        """True if any frame above us belongs to clients/dashboards/*."""
        frame = sys._getframe(1)
        depth = 0
        while frame is not None and depth < 40:
            fname = frame.f_code.co_filename
            if cls._SUB_DASHBOARD_PATH in fname:
                return True
            frame = frame.f_back
            depth += 1
        return False

    def flush(self):
        self.original.flush()

    @staticmethod
    def _classify(text: str) -> tuple[str, str]:
        """Extract log level and source from bracket-tagged log lines."""
        level = "info"
        source = "general"

        if "[error]" in text.lower() or "error" in text.lower() or "failed" in text.lower():
            level = "error"
        elif "[warning]" in text.lower():
            level = "warning"

        tag_match = _TAG_RE.search(text)
        if tag_match:
            tag = tag_match.group(1).lower()
            if tag in ("tool", "mcp", "code"):
                source = "tool"
            elif tag in ("memory", "extract", "dedup", "consolidate"):
                source = "memory"
            elif tag in ("tokens", "context"):
                source = "tokens"
            elif tag in ("sleep",):
                source = "sleep"
            elif tag in ("dashboard",):
                source = "dashboard"
            elif tag in ("ingest", "code_ingest"):
                source = "ingest"
            else:
                source = tag

        return level, source


async def _prune_logs_loop():
    """Periodically delete Activity Log entries older than the retention window."""
    while True:
        try:
            removed = await asyncio.to_thread(db.prune_logs, config.LOG_RETENTION_DAYS)
            if removed:
                print(f"  [dashboard] Pruned {removed} logs older than {config.LOG_RETENTION_DAYS} days")
        except Exception:
            pass
        await asyncio.sleep(3600)  # hourly


class _QuietLightsFilter(logging.Filter):
    """Suppress access log noise from iPad polling /api/lights every 4s."""
    def filter(self, record):
        msg = record.getMessage()
        if "/api/lights" in msg:
            return False
        return True


def create_app():
    app = Quart(__name__)
    app.secret_key = get_secret("dashboard-secret-key")

    # Suppress /api/lights polling from access logs
    logging.getLogger("quart.serving").addFilter(_QuietLightsFilter())
    logging.getLogger("hypercorn.access").addFilter(_QuietLightsFilter())

    # Initialize database
    db.init_db()

    # Shared state
    app.log_buffer = collections.deque(maxlen=500)
    app.log_subscribers = set()
    app.sleep_running = False

    @app.before_serving
    async def startup():
        # Capture stdout here (after reloader fork, so it sticks)
        if not isinstance(sys.stdout, LogCapture):
            app.original_stdout = sys.stdout
            sys.stdout = LogCapture(sys.stdout, app.log_buffer, app.log_subscribers)
        app.agent = AgentCore(
            enable_tools=True,
            session_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory", "data", "session_dashboard.json"),
            threads=config.THREADS_MODE != "off",
        )
        await app.agent.start()
        app.vector_store = app.agent.memory.vector_store
        app.prune_task = asyncio.create_task(_prune_logs_loop())
        print("  [dashboard] Agent started")

        # Trigger engine: webhook firings come in via routes/hooks.py; poll
        # sources run in a background loop. Lives here because this is the
        # always-on process with both the HTTP server and a running ToolRouter.
        from trigger_engine import TriggerEngine
        app.trigger_engine = TriggerEngine(agent=app.agent)
        app.trigger_poll_task = asyncio.create_task(app.trigger_engine.poll_loop())

        # Pending iMessage reply watches: when someone answers a question the
        # agent texted them, wake the agent with the reply and the follow-up
        # intent. Shares the trigger engine's prompt lock (one AgentCore at a
        # time) by borrowing its run_prompt.
        import reply_watch
        app.reply_watch_task = asyncio.create_task(
            reply_watch.watch_loop(app.trigger_engine.run_prompt))

        # Proactive calendar heads-ups: plans which upcoming events deserve a
        # spoken nudge and writes one-time scheduler tasks for them. Lives here
        # (not in the scheduler daemon) because it re-plans off calendar changes.
        import calendar_briefing
        app.briefing_task = asyncio.create_task(calendar_briefing.briefing_loop())

        # The voice assistant is now a standalone, decoupled service
        # (see ../voice_assistant). It is started independently and talks to
        # the dashboard only over the /api/inference text endpoint.

    @app.after_serving
    async def shutdown():
        # Stop log pruning task
        if getattr(app, "prune_task", None):
            app.prune_task.cancel()
        if getattr(app, "trigger_poll_task", None):
            app.trigger_poll_task.cancel()
        if getattr(app, "reply_watch_task", None):
            app.reply_watch_task.cancel()
        if getattr(app, "briefing_task", None):
            app.briefing_task.cancel()

        await app.agent.shutdown()
        if hasattr(app, 'original_stdout'):
            sys.stdout = app.original_stdout
        print("  [dashboard] Agent stopped")

    # Register blueprints
    from dashboard.auth import auth_bp
    from dashboard.routes.chat import chat_bp
    from dashboard.routes.memory import memory_bp
    from dashboard.routes.tasks import tasks_bp
    from dashboard.routes.sleep import sleep_bp
    from dashboard.routes.tools import tools_bp
    from dashboard.routes.config_routes import config_bp
    from dashboard.routes.logs import logs_bp
    from dashboard.routes.costs import costs_bp
    from dashboard.routes.gesture import gesture_bp
    from dashboard.routes.inference import inference_bp
    from dashboard.routes.lights import lights_bp
    from dashboard.routes.dashboards import dashboards_bp, register_dashboard_apis
    from dashboard.routes.projects import projects_bp
    from dashboard.routes.workflows import workflows_bp
    from dashboard.routes.hooks import hooks_bp
    from dashboard.routes.triggers import triggers_bp
    from dashboard.routes.ingest import ingest_bp
    from dashboard.routes.toolbus import toolbus_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(memory_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(sleep_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(costs_bp)
    app.register_blueprint(gesture_bp)
    app.register_blueprint(inference_bp)
    app.register_blueprint(lights_bp)
    app.register_blueprint(dashboards_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(workflows_bp)
    app.register_blueprint(hooks_bp)
    app.register_blueprint(triggers_bp)
    app.register_blueprint(ingest_bp)
    app.register_blueprint(toolbus_bp)

    # Load API blueprints from clients/dashboards/*/api.py
    register_dashboard_apis(app)

    return app
