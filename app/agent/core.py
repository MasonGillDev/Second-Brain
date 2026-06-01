"""
Agent Core — shared brain for all interfaces (CLI, Telegram, etc.).

Handles the tool-use loop, memory, and LLM communication.
Interfaces just call `agent.process(message)` and get a response.
"""

import asyncio
import json
import os
import sys
import config
from memory.manager import MemoryManager
from skills.router import ToolRouter
from adapters.base import Usage


def create_adapter():
    """Factory: create the right adapter based on config."""
    if config.LLM_PROVIDER == "claude":
        from adapters.claude import ClaudeAdapter
        return ClaudeAdapter()
    elif config.LLM_PROVIDER == "openrouter":
        from adapters.openrouter import OpenRouterAdapter
        return OpenRouterAdapter()
    else:
        raise ValueError(f"Unknown provider: {config.LLM_PROVIDER}")


class AgentCore:
    def __init__(self, enable_tools: bool = True, session_file: str | None = None):
        """
        Args:
            enable_tools: If False, skip MCP server startup (for lightweight
                          processes like the scheduler that only need LLM + memory).
            session_file: Optional path to conversation session file.
                          Defaults to config.SESSION_FILE.
        """
        self.memory = MemoryManager(session_file=session_file)
        self.router = ToolRouter()
        self.adapter = create_adapter()
        self._enable_tools = enable_tools and config.TOOLS_ENABLED
        self._started = False
        self._cancelled = False
        self._active_task: asyncio.Task | None = None
        self.on_tool_call = None

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

    def cancel(self):
        """Cancel the current processing loop and any active subprocesses."""
        self._cancelled = True
        # Signal the code server to kill its subprocess
        os.makedirs(os.path.dirname(config.CANCEL_SIGNAL_FILE), exist_ok=True)
        with open(config.CANCEL_SIGNAL_FILE, "w") as f:
            f.write("cancel")
        if self._active_task and not self._active_task.done():
            self._active_task.cancel()
        print("  [cancel] Cancellation requested")

    def _build_tools(self) -> list[dict] | None:
        """Get current tools: meta-tools + always-on + activated skills."""
        if not self._enable_tools:
            return None
        all_tools = self.router.get_tools()
        return self.adapter.format_tools(all_tools) if all_tools else None

    async def process(self, user_input: str, images: list[dict] | None = None,
                      source: str = "unknown") -> str:
        """
        Process a user message and return the agent's response.
        Handles memory, tool routing, and the multi-round tool-use loop.

        Args:
            user_input: The user's text message.
            images: Optional list of image dicts with keys:
                    - "data": base64-encoded image data
                    - "media_type": e.g. "image/png", "image/jpeg"
            source: Where this request came from (dashboard, telegram, scheduler, cli).
        """
        # Reload config overrides (picks up dashboard changes without restart)
        config.reload_overrides()

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

        # Store images for this request (used when building messages)
        self._pending_images = images

        # Add user message to conversation memory
        self.memory.add_user_message(user_input)

        # Reset cancellation state and register this task so cancel() can interrupt it
        self._cancelled = False
        self._active_task = asyncio.current_task()
        if os.path.exists(config.CANCEL_SIGNAL_FILE):
            os.remove(config.CANCEL_SIGNAL_FILE)

        # Build context
        system_prompt, messages = self.memory.build_messages(user_input)
        original_msg_count = len(messages)

        # Voice mode: override response style for spoken output
        if source == "voice":
            system_prompt += (
                "\n\n## Voice Mode\n"
                "The user is speaking to you via voice. Respond in natural spoken language. "
                "No markdown, no bullet points, no numbered lists, no code blocks, no special formatting. "
                "Keep responses conversational, concise, and easy to listen to."
            )

        self._last_system_prompt = system_prompt
        self._last_messages = messages

        # Inject images into the last user message if present
        if self._pending_images:
            for msg in reversed(messages):
                if msg["role"] == "user" and isinstance(msg["content"], str):
                    content_blocks = [
                        self.adapter.format_image_block(img)
                        for img in self._pending_images
                    ]
                    content_blocks.append({"type": "text", "text": msg["content"]})
                    msg["content"] = content_blocks
                    break
            self._pending_images = None

        # Build initial tool set (always-on + meta-tools, no activated skills yet)
        tools = self._build_tools()

        # Tool-use loop
        total_usage = Usage()
        total_tool_calls = 0
        response = None

        try:
            for round_num in range(config.MAX_TOOL_ROUNDS):
                if self._cancelled:
                    break

                response = await self.adapter.chat(system_prompt, messages, tools)
                total_usage = total_usage + response.usage

                if not response.tool_calls:
                    break

                # Append assistant message with tool_use blocks
                messages.append(self.adapter.format_assistant_message(response.raw_message))

                # Execute tools
                tool_results = []
                tools_changed = False

                total_tool_calls += len(response.tool_calls)

                for tc in response.tool_calls:
                    if self._cancelled:
                        break
                    # Handle activate_skill meta-tool locally
                    if tc.name == "activate_skill":
                        skill_name = tc.arguments.get("skill_name", "")
                        result = self.router.activate_skill(skill_name)
                        tool_results.append((tc.id, result))
                        tools_changed = True
                        if config.LOG_TOKEN_USAGE:
                            print(f"  [skill] Activated: {skill_name}")
                        continue

                    if self.on_tool_call:
                        self.on_tool_call(tc.name, tc.arguments)

                    if isinstance(tc.arguments, dict) and "__parse_error__" in tc.arguments:
                        result = f"[ERROR] Could not parse tool arguments: {tc.arguments['__parse_error__']}"
                    else:
                        result = await self.router.call_tool(tc.name, tc.arguments)

                    # Persist the full call + result to the Activity Log (expandable),
                    # before truncating the copy that goes back to the model.
                    self._log_tool_call(tc.name, tc.arguments, result)

                    if len(result) > 5000:
                        result = result[:5000] + "\n[...truncated]"

                    tool_results.append((tc.id, result))

                tool_result_msg = self.adapter.format_tool_results(tool_results)
                if isinstance(tool_result_msg, list):
                    messages.extend(tool_result_msg)
                else:
                    messages.append(tool_result_msg)

                if self._cancelled:
                    break

                # Rebuild tool list if skills were activated this round
                if tools_changed:
                    tools = self._build_tools()

            # Hit the round cap while the agent still wanted to call tools:
            # make one final call WITHOUT tools so it answers from the results
            # gathered so far, instead of returning the empty/partial text that
            # accompanied the last tool call.
            if response and response.tool_calls and not self._cancelled:
                print(f"  [warning] Hit max tool rounds ({config.MAX_TOOL_ROUNDS}); requesting final answer")
                response = await self.adapter.chat(system_prompt, messages, None)
                total_usage = total_usage + response.usage
        except asyncio.CancelledError:
            # cancel() called _active_task.cancel(); treat as a clean cancellation
            self._cancelled = True

        if self._cancelled:
            assistant_text = "Cancelled."
        else:
            assistant_text = (response.text if response else "") or ""

        # Persist the full agent reply to the Activity Log (expandable)
        if not self._cancelled:
            self._log_agent_reply(assistant_text)

        # Log token usage
        if config.LOG_TOKEN_USAGE:
            input_cost = (total_usage.input_tokens / 1000) * config.INPUT_COST_PER_1K
            output_cost = (total_usage.output_tokens / 1000) * config.OUTPUT_COST_PER_1K
            print(f"  [tokens] in: {total_usage.input_tokens} | out: {total_usage.output_tokens} | cost: ${input_cost + output_cost:.4f}")

        # Persist cost to database
        import db
        cost = db.compute_cost(config.MODEL, total_usage.input_tokens, total_usage.output_tokens)
        db.log_api_call(
            source=source,
            model=config.MODEL,
            input_tokens=total_usage.input_tokens,
            output_tokens=total_usage.output_tokens,
            cost_usd=cost,
            tool_calls_count=total_tool_calls,
        )

        # Bake tool call context into the saved message so it persists,
        # but return the clean response to the user
        saved_text = assistant_text
        tool_loop_messages = messages[original_msg_count:]
        if tool_loop_messages:
            tool_text = self._tool_messages_to_text(tool_loop_messages)
            if tool_text:
                saved_text = f"[Tool calls]\n{tool_text}\n\n[Response]\n{assistant_text}"

        # Store in conversation memory and persist session
        self.memory.add_assistant_message(saved_text)
        self.memory.conversation.save_session()

        return assistant_text

    @staticmethod
    def _cap(text: str) -> str:
        """Cap a log detail blob at LOG_DETAIL_MAX_BYTES, marking truncation."""
        cap = config.LOG_DETAIL_MAX_BYTES
        if len(text) <= cap:
            return text
        return text[:cap] + f"\n[...truncated at {cap // 1024} KB]"

    def _log_tool_call(self, name: str, arguments, result: str):
        """Persist a full tool call + result as one expandable Activity Log entry."""
        if not config.LOG_TOKEN_USAGE:
            return
        try:
            args_str = (json.dumps(arguments, indent=2, default=str)
                        if isinstance(arguments, (dict, list)) else str(arguments))
        except Exception:
            args_str = str(arguments)
        preview = " ".join(args_str.split())[:80]
        summary = f"{name}({preview})"
        details = (f"▼ Arguments\n{self._cap(args_str)}\n\n"
                   f"▼ Result ({len(result):,} chars)\n{self._cap(result)}")
        try:
            sys.__stdout__.write(f"  [tool] {summary}\n")  # console echo, not re-captured to DB
        except Exception:
            pass
        try:
            import db
            db.log_message("info", "tool", summary, details=details)
        except Exception:
            pass

    def _log_agent_reply(self, text: str):
        """Persist the full agent reply as an expandable Activity Log entry."""
        if not config.LOG_TOKEN_USAGE or not text:
            return
        preview = " ".join(text.split())[:80]
        details = self._cap(text) if (len(text.strip()) > 80 or "\n" in text) else None
        try:
            import db
            db.log_message("info", "agent", preview, details=details)
        except Exception:
            pass

    @staticmethod
    def _tool_messages_to_text(tool_messages: list[dict]) -> str:
        """Convert tool loop messages to plain text, handling any content format."""
        lines = []
        for msg in tool_messages:
            content = msg.get("content")
            if content is None:
                continue
            # String content — just include it
            if isinstance(content, str):
                if content.strip():
                    lines.append(content.strip())
                continue
            # List of blocks
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, str):
                        if block.strip():
                            lines.append(block.strip())
                    elif isinstance(block, dict):
                        text = block.get("text") or block.get("content") or ""
                        name = block.get("name", "")
                        inp = block.get("input")
                        if name and inp is not None:
                            args = json.dumps(inp)
                            if len(args) > 300:
                                args = args[:300] + "..."
                            lines.append(f"Called: {name}({args})")
                        if isinstance(text, str) and text.strip():
                            t = text.strip()
                            if len(t) > 1000:
                                t = t[:1000] + "..."
                            lines.append(t)
                    else:
                        s = str(block).strip()
                        if s:
                            lines.append(s)
                continue
            # Fallback
            s = str(content).strip()
            if s:
                lines.append(s)
        return "\n".join(lines)

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
