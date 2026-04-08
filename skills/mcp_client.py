"""
MCP Client wrapper.

Manages a single MCP server subprocess. Provides async methods to
list available tools and call them. The server communicates over
stdin/stdout — nothing leaves the machine.
"""

import os
from contextlib import AsyncExitStack
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters


class MCPClient:
    def __init__(self, server_name: str, command: str, args: list[str], env: dict | None = None):
        self.server_name = server_name
        self.command = command
        self.args = args
        self.env = env
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._tools_cache: list[dict] | None = None

    async def start(self):
        """Start the MCP server subprocess and initialize the session."""
        server_env = os.environ.copy()
        if self.env:
            server_env.update(self.env)

        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=server_env,
        )

        self._exit_stack = AsyncExitStack()
        transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

    async def stop(self):
        """Stop the MCP server subprocess."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except (Exception, BaseException):
                pass  # Suppress anyio cancel scope errors on shutdown
            self._exit_stack = None
            self._session = None
            self._tools_cache = None

    async def list_tools(self) -> list[dict]:
        """
        Get available tools from this server.
        Returns provider-agnostic tool definitions with namespaced names.
        """
        if self._tools_cache is not None:
            return self._tools_cache

        if not self._session:
            raise RuntimeError(f"MCP server '{self.server_name}' not started")

        result = await self._session.list_tools()
        tools = []
        for tool in result.tools:
            tools.append({
                "name": f"{self.server_name}__{tool.name}",
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            })

        self._tools_cache = tools
        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Call a tool on this server.
        tool_name should be the original name (without server prefix).
        Returns the result as a string.
        """
        if not self._session:
            raise RuntimeError(f"MCP server '{self.server_name}' not started")

        result = await self._session.call_tool(tool_name, arguments)

        # Combine all content blocks into a single string
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
            else:
                parts.append(str(block))

        text = "\n".join(parts)

        if result.isError:
            return f"[ERROR] {text}"

        return text
