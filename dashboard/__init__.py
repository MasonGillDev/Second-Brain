"""
Second Brain Dashboard — Quart app factory.
"""

import sys
import io
import time
import collections
from quart import Quart

from core import AgentCore
from memory.vector_store import VectorStore
from keychain import get_secret


class LogCapture(io.TextIOBase):
    """Tee stdout to both console and an in-memory ring buffer."""

    def __init__(self, original, buffer, subscribers):
        self.original = original
        self.buffer = buffer
        self.subscribers = subscribers

    def write(self, text):
        self.original.write(text)
        if text.strip():
            entry = {"ts": time.time(), "text": text.strip()}
            self.buffer.append(entry)
        return len(text)

    def flush(self):
        self.original.flush()


def create_app():
    app = Quart(__name__)
    app.secret_key = get_secret("dashboard-secret-key")

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(memory_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(sleep_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(logs_bp)

    return app
