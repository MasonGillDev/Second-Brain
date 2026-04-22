"""
Second Brain Dashboard — Quart app factory.
"""

import sys
import io
import re
import time
import collections
from quart import Quart

from core import AgentCore
from memory.vector_store import VectorStore
from keychain import get_secret
import db


# Pattern to extract [tag] from log lines
_TAG_RE = re.compile(r'\[(\w+)\]')


class LogCapture(io.TextIOBase):
    """Tee stdout to both console, an in-memory ring buffer, and SQLite."""

    def __init__(self, original, buffer, subscribers):
        self.original = original
        self.buffer = buffer
        self.subscribers = subscribers

    # Endpoints to exclude from log capture (prevent feedback loops)
    _SKIP_PATTERNS = ("/api/logs", "/api/costs")

    def write(self, text):
        self.original.write(text)
        if text.strip():
            msg = text.strip()

            # Skip logging requests to our own polling endpoints
            if any(p in msg for p in self._SKIP_PATTERNS):
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


def create_app():
    app = Quart(__name__)
    app.secret_key = get_secret("dashboard-secret-key")

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
            session_file="./memory/data/session_dashboard.json",
        )
        await app.agent.start()
        app.vector_store = app.agent.memory.vector_store
        print("  [dashboard] Agent started")

    @app.after_serving
    async def shutdown():
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(memory_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(sleep_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(costs_bp)

    return app
