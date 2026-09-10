"""
Second Brain Dashboard — Entry point.

Usage:
    python app/main.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The dashboard is the SOLE owner of the Cync cloud connection. The Cync cloud
# evicts a second concurrent session, so only this process opens a real pycync
# connection; every other agent (telegram, scheduler) proxies Cync commands to
# the dashboard's REST API. The flag is inherited by the light_server subprocess
# (MCPClient copies os.environ into each server). See light_server.py.
os.environ.setdefault("CYNC_OWNER", "1")

from dashboard import create_app

app = create_app()

if __name__ == "__main__":
    # Debug/reloader is OPT-IN (DASHBOARD_DEBUG=1) and must stay OFF under
    # launchd: the reloader re-execs on any .py edit WITHOUT gracefully
    # shutting down the old agent, leaving a second full stack of MCP server
    # subprocesses (two music/light/tv servers racing AppleScript and the Cync
    # session, two trigger pollers, two ThreadManagers on one index). It also
    # confuses launchd's process tracking (the pid=-/no-relaunch flakiness).
    _debug = os.environ.get("DASHBOARD_DEBUG") == "1"
    app.run(host="0.0.0.0", port=5001, debug=_debug, use_reloader=_debug)
