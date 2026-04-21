"""
Second Brain Dashboard — Entry point.

Usage:
    python dashboard_server.py
"""

from dashboard import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
