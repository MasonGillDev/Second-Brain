"""
Agent Core — shared brain for all interfaces (CLI, Telegram, etc.).

Handles the tool-use loop, memory, and LLM communication.
Interfaces just call `agent.process(message)` and get a response.
"""

from dotenv import load_dotenv
load_dotenv()

import config
from memory.manager import MemoryManager
from skills.router import ToolRouter
from adapters.base import Usage


def create_adapter():
    """Factory: create the right adapter based on config."""
    if config.LLM_PROVIDER == "claude":
        from adapters.claude import ClaudeAdapter
        return ClaudeAdapter()
    else:
        raise ValueError(f"Unknown provider: {config.LLM_PROVIDER}")


class AgentCore:
    def __init__(self, enable_tools: bool = True):
        """
        Args:
            enable_tools: If False, skip MCP server startup (for lightweight
                          processes like the scheduler that only need LLM + memory).
        """
        self.memory = MemoryManager()
        self.router = ToolRouter()
        self.adapter = create_adapter()
        self._enable_tools = enable_tools and config.TOOLS_ENABLED
        self._started = False

    async def start(self):
        """Start MCP servers. Call once before processing messages."""
        if self._enable_tools:
            await self.router.start()
        self._started = True

    async def shutdown(self):
        """Stop MCP servers and save session."""
        if config.AUTO_EXTRACT_MEMORIES:
            self.memory.extract_memories()
        if config.CONSOLIDATE_ON_SHUTDOWN:
            stats = self.memory.consolidate_memories()
            if config.LOG_TOKEN_USAGE:
                if stats.get("clusters_found", 0) > 0:
                    print(f"  [consolidate] Merged {stats['clusters_found']} clusters: {stats['memories_before']} → {stats['memories_after']} memories")
                else:
                    print(f"  [consolidate] No clusters found ({stats.get('memories_before', 0)} memories checked)")
        self.memory.conversation.save_session()
        if self._enable_tools:
            try:
                await self.router.shutdown()
            except (Exception, BaseException):
                pass

    async def process(self, user_input: str) -> str:
        """
        Process a user message and return the agent's response.
        Handles memory, tool routing, and the multi-round tool-use loop.
        """
        # Handle /remember command from any interface
        if user_input.startswith("/remember "):
            text = user_input[10:].strip()
            if text:
                doc_id = self.memory.remember(text)
                return f"Stored in long-term memory (id: {doc_id})"
            return "Usage: /remember <something to remember>"

        if user_input.strip() == "/stats":
            return self._format_stats()

        if user_input.strip() == "/memories":
            return self._format_memories()

        # Add user message to conversation memory
        self.memory.add_user_message(user_input)

        # Build context
        system_prompt, messages = self.memory.build_messages(user_input)

        # Route: only include tools relevant to this message
        matched_tools = self.router.get_tools(user_input)
        tools = self.adapter.format_tools(matched_tools) if matched_tools else None

        # Tool-use loop
        total_usage = Usage()

        for round_num in range(config.MAX_TOOL_ROUNDS):
            response = await self.adapter.chat(system_prompt, messages, tools)
            total_usage = total_usage + response.usage

            if not response.tool_calls:
                break

            # Append assistant message with tool_use blocks
            messages.append(self.adapter.format_assistant_message(response.raw_message))

            # Execute tools
            tool_results = []
            for tc in response.tool_calls:
                if config.LOG_TOKEN_USAGE:
                    args_preview = str(tc.arguments)[:80]
                    print(f"  [tool] {tc.name}({args_preview})")

                result = await self.router.call_tool(tc.name, tc.arguments)

                if len(result) > 5000:
                    result = result[:5000] + "\n[...truncated]"

                tool_results.append((tc.id, result))

            messages.append(self.adapter.format_tool_results(tool_results))

            if round_num == config.MAX_TOOL_ROUNDS - 1:
                print(f"  [warning] Hit max tool rounds ({config.MAX_TOOL_ROUNDS})")

        assistant_text = response.text or ""

        # Log token usage
        if config.LOG_TOKEN_USAGE:
            input_cost = (total_usage.input_tokens / 1000) * config.INPUT_COST_PER_1K
            output_cost = (total_usage.output_tokens / 1000) * config.OUTPUT_COST_PER_1K
            print(f"  [tokens] in: {total_usage.input_tokens} | out: {total_usage.output_tokens} | cost: ${input_cost + output_cost:.4f}")

        # Store in conversation memory
        self.memory.add_assistant_message(assistant_text)

        return assistant_text

    def _format_stats(self) -> str:
        stats = self.memory.get_stats()
        lines = ["Memory Statistics:"]
        lines.append(f"  Conversation: {stats['conversation']['recent_messages']} recent messages, {stats['conversation']['total_processed']} total")
        lines.append(f"  Summary: ~{stats['conversation']['summary_tokens_est']} tokens")
        for name, count in stats['vector_store'].items():
            lines.append(f"  {name}: {count} entries")
        return "\n".join(lines)

    def _format_memories(self) -> str:
        """Dump all long-term memories directly from ChromaDB."""
        collection = self.memory.vector_store.collections["long_term"]
        if collection.count() == 0:
            return "No long-term memories stored."

        results = collection.get(limit=50)
        lines = [f"Long-Term Memories ({collection.count()} total):\n"]
        for doc_id, text, meta in zip(
            results["ids"], results["documents"], results["metadatas"]
        ):
            category = meta.get("category", meta.get("type", ""))
            access_count = meta.get("access_count", 0)
            lines.append(f"  [{doc_id}] ({category}) x{access_count} — {text}")
        return "\n".join(lines)
