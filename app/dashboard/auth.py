"""
Authentication for the dashboard.
Password stored in macOS Keychain. Session cookie for auth state.
"""

import functools
import hmac
from quart import Blueprint, request, session, redirect, url_for, render_template, jsonify
from keychain import get_secret

auth_bp = Blueprint("auth", __name__)


def require_auth(f):
    """Decorator: redirect to login if not authenticated."""
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("auth.login"))
        return await f(*args, **kwargs)
    return wrapper


def require_ws_auth():
    """Check auth for websocket connections. Returns True if authenticated."""
    return session.get("authenticated", False)


@auth_bp.route("/login", methods=["GET"])
async def login():
    return await render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
async def login_post():
    form = await request.form
    password = form.get("password", "")
    try:
        correct = get_secret("dashboard-password")
    except RuntimeError:
        return await render_template("login.html", error="Dashboard password not configured in Keychain")

    if hmac.compare_digest(password, correct):
        session["authenticated"] = True
        session.permanent = True
        return redirect(url_for("auth.dashboard"))
    return await render_template("login.html", error="Wrong password")


@auth_bp.route("/logout")
async def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/")
@require_auth
async def dashboard():
    return await render_template("index.html")
