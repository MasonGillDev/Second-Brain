"""
Tool Router.

Manages all MCP server connections and provides a unified interface
for discovering and calling tools. Provider-agnostic — knows nothing
about Claude or OpenAI formats.
"""

import config
from skills.mcp_client import MCPClient


class ToolRouter:
    def __init__(self):
        self._clients: dict[str, MCPClient] = {}
        self._tools: list[dict] = []

    async def start(self):
        """Start all configured MCP servers and discover their tools."""
        if not config.TOOLS_ENABLED:
            return

        for name, server_config in config.MCP_SERVERS.items():
            client = MCPClient(
                server_name=name,
                command=server_config["command"],
                args=server_config["args"],
                env=server_config.get("env"),
            )
            try:
                await client.start()
                tools = await client.list_tools()

                # Filter by allowlist if configured
                allowlist = getattr(config, "TOOL_ALLOWLIST", {}).get(name)
                if allowlist is not None:
                    # tool names are "server__tool_name", allowlist has just "tool_name"
                    tools = [t for t in tools if t["name"].split("__", 1)[1] in allowlist]

                self._clients[name] = client
                self._tools.extend(tools)
                if config.LOG_TOKEN_USAGE:
                    tool_names = [t["name"] for t in tools]
                    print(f"  [mcp] {name}: {len(tools)} tools — {tool_names[:5]}{'...' if len(tools) > 5 else ''}")
            except Exception as e:
                print(f"  [mcp] Failed to start '{name}': {e}")

    async def shutdown(self):
        """Stop all MCP servers."""
        for name, client in self._clients.items():
            try:
                await client.stop()
            except Exception as e:
                print(f"  [mcp] Error stopping '{name}': {e}")
        self._clients.clear()
        self._tools.clear()

    def get_tools(self, query: str = "") -> list[dict]:
        """
        Get available tool definitions.
        If query is provided, only return tools from servers whose
        keywords match the query (saves tokens). If no match, returns
        no tools. Pass empty string to get all tools.
        """
        if not query or not hasattr(config, "TOOL_ROUTING"):
            return self._tools

        query_lower = query.lower()

        # Always include these servers
        always = set(getattr(config, "ALWAYS_INCLUDE_SERVERS", []))
        matched_servers = set(always)

        for server_name, keywords in config.TOOL_ROUTING.items():
            for keyword in keywords:
                if keyword in query_lower:
                    matched_servers.add(server_name)
                    break

        if not matched_servers:
            return []

        filtered = [
            t for t in self._tools
            if t["name"].split("__")[0] in matched_servers
        ]

        if config.LOG_TOKEN_USAGE and filtered:
            servers = ", ".join(matched_servers)
            print(f"  [routing] Matched servers: {servers} ({len(filtered)} tools)")

        return filtered

    async def call_tool(self, namespaced_name: str, arguments: dict) -> str:
        """
        Call a tool by its namespaced name (e.g., 'filesystem__read_file').
        Returns the result as a string.
        """
        parts = namespaced_name.split("__", 1)
        if len(parts) != 2:
            return f"[ERROR] Invalid tool name format: {namespaced_name}"

        server_name, tool_name = parts

        client = self._clients.get(server_name)
        if not client:
            return f"[ERROR] Unknown server: {server_name}"

        try:
            return await client.call_tool(tool_name, arguments)
        except Exception as e:
            return f"[ERROR] Tool call failed: {e}"
