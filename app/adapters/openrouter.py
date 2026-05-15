"""
OpenRouter adapter.

Translates between the provider-agnostic tool format and
OpenRouter's OpenAI-compatible API for tool calls.
"""

import json
import uuid
import httpx
import config
from adapters.base import LLMAdapter, AdapterResponse, ToolCall, Usage
from keychain import get_secret


class OpenRouterAdapter(LLMAdapter):
    def __init__(self):
        self._api_key = get_secret("openrouter-api-key")
        self._base_url = "https://openrouter.ai/api/v1"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )

    def format_tools(self, tools: list[dict]) -> list[dict]:
        """Convert to OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in tools
        ]

    async def chat(self, system: str, messages: list[dict], tools: list[dict] | None = None) -> AdapterResponse:
        """Send a message to OpenRouter, returns an AdapterResponse."""
        # Build messages with system prompt first
        api_messages = [{"role": "system", "content": system}] + messages

        payload = {
            "model": config.MODEL,
            "max_tokens": config.MAX_RESPONSE_TOKENS,
            "messages": api_messages,
        }
        if tools:
            payload["tools"] = tools

        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        message = choice["message"]

        # Parse text
        text = message.get("content")

        # Parse tool calls
        tool_calls = []
        for tc in message.get("tool_calls") or []:
            func = tc["function"]
            args = func.get("arguments", "{}")
            if isinstance(args, str):
                args = json.loads(args)
            tool_calls.append(ToolCall(
                id=tc["id"],
                name=func["name"],
                arguments=args,
            ))

        # Map finish reason
        finish = choice.get("finish_reason", "stop")
        stop_reason = "tool_use" if finish == "tool_calls" else "end_turn"

        # Parse usage
        usage_data = data.get("usage", {})

        return AdapterResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            raw_message=message,
            usage=Usage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
            ),
        )

    def format_assistant_message(self, raw_message) -> dict:
        """Convert OpenAI-format response into a message dict for history."""
        msg = {"role": "assistant"}

        if raw_message.get("content"):
            msg["content"] = raw_message["content"]

        if raw_message.get("tool_calls"):
            msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                            if isinstance(tc["function"]["arguments"], str)
                            else json.dumps(tc["function"]["arguments"]),
                    },
                }
                for tc in raw_message["tool_calls"]
            ]

        return msg

    def format_tool_results(self, results: list[tuple[str, str]]) -> list[dict]:
        """
        Format tool results. OpenAI format uses separate messages per tool result,
        each with role=tool. Returns a list — the agent loop must handle this.
        """
        return [
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_text,
            }
            for tool_call_id, result_text in results
        ]
