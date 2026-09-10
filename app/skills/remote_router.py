"""
Remote Tool Router.

A drop-in replacement for ToolRouter used by every process that is NOT the
dashboard (telegram bot, scheduler). Instead of spawning its own MCP server
subprocesses — which used to leave two light/music/tv servers racing each other
(and the Cync cloud evicting whichever session connected second) — it forwards
tool discovery and every tool call over loopback HTTP to the dashboard's
toolbus endpoints (dashboard/routes/toolbus.py), where the single real
ToolRouter instance executes them.

All the skill-manifest / activation / allowlist logic is inherited from
ToolRouter unchanged; only start(), shutdown(), and call_tool() differ.
"""

import asyncio
import json
import urllib.error
import urllib.request

import config
from keychain import get_secret
from skills.router import ToolRouter

# The dashboard can run tool calls that take minutes (Claude Code, workflows).
# Per-socket-op timeout, so it only fires if the dashboard goes silent.
CALL_TIMEOUT = 900
# How long start() waits for the dashboard to come up (launchd starts all
# services at boot in no particular order).
STARTUP_WAIT = 60


class RemoteToolRouter(ToolRouter):
    def __init__(self):
        super().__init__()
        self._base = getattr(config, "TOOLBUS_URL", "http://127.0.0.1:5001").rstrip("/")
        self._api_key: str | None = None

    def _request(self, path: str, method: str = "GET", body: dict | None = None,
                 timeout: float = CALL_TIMEOUT):
        if self._api_key is None:
            self._api_key = get_secret("watch-api-key")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self._base}{path}", data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._api_key}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    async def _fetch_tools(self) -> bool:
        """Pull the dashboard's discovered tool list. True on success."""
        try:
            data = await asyncio.to_thread(self._request, "/api/toolbus/tools", "GET", None, 10)
        except (urllib.error.URLError, OSError, ValueError):
            return False
        self._tools = data.get("tools", [])
        if config.LOG_TOKEN_USAGE:
            servers = {t["name"].split("__", 1)[0] for t in self._tools}
            print(f"  [mcp] toolbus: {len(self._tools)} tools from {len(servers)} "
                  f"servers via {self._base}")
        return True

    async def start(self):
        """Discover tools from the dashboard instead of spawning servers."""
        if not config.TOOLS_ENABLED:
            return
        deadline = asyncio.get_event_loop().time() + STARTUP_WAIT
        while not await self._fetch_tools():
            if asyncio.get_event_loop().time() >= deadline:
                print(f"  [mcp] toolbus unreachable at {self._base} after "
                      f"{STARTUP_WAIT}s — will retry on first tool call")
                return
            await asyncio.sleep(2)

    async def shutdown(self):
        """Nothing to stop — the dashboard owns the MCP servers."""
        self._tools.clear()

    async def call_tool(self, namespaced_name: str, arguments: dict) -> str:
        # Dashboard may have (re)started after we did — recover the tool list
        # lazily so a restart on either side heals without intervention.
        if not self._tools:
            await self._fetch_tools()
        try:
            data = await asyncio.to_thread(
                self._request, "/api/toolbus/call", "POST",
                {"name": namespaced_name, "arguments": arguments})
            return data.get("result", "")
        except Exception as e:
            return (f"[ERROR] Tool call failed: toolbus at {self._base} "
                    f"unreachable (is the dashboard running?): {e}")
