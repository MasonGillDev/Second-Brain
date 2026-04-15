"""
Claude (Anthropic) adapter.

Translates between the provider-agnostic tool format and
Anthropic's API for tool_use / tool_result messages.
"""

import anthropic
import config
from adapters.base import LLMAdapter, AdapterResponse, ToolCall, Usage
from keychain import get_secret


class ClaudeAdapter(LLMAdapter):
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=get_secret("anthropic-api-key"))

    def format_tools(self, tools: list[dict]) -> list[dict]:
        """
        Claude's tool format is nearly identical to our agnostic format.
        Just pass through — Claude expects: name, description, input_schema.
        """
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            for tool in tools
        ]

    async def chat(self, system: str, messages: list[dict], tools: list[dict] | None = None) -> AdapterResponse:
        """Send a message to Claude, returns an AdapterResponse."""
        kwargs = {
            "model": config.MODEL,
            "max_tokens": config.MAX_RESPONSE_TOKENS,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._client.messages.create(**kwargs)

        # Parse response content blocks
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                ))

        return AdapterResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            raw_message=response,
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )

    def format_assistant_message(self, raw_message) -> dict:
        """
        Convert Claude's response into a message dict for the conversation history.
        Must preserve both text and tool_use blocks.
        """
        content = []
        for block in raw_message.content:
            if block.type == "text":
                content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        return {"role": "assistant", "content": content}

    def format_tool_results(self, results: list[tuple[str, str]]) -> dict:
        """
        Format tool results as a user message with tool_result blocks.
        Claude requires tool results in the user turn immediately after
        the assistant turn that contained the tool_use blocks.
        """
        content = []
        for tool_call_id, result_text in results:
            content.append({
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": result_text,
            })
        return {"role": "user", "content": content}
