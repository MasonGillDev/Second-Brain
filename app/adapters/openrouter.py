"""
OpenRouter adapter.

Translates between the provider-agnostic tool format and
OpenRouter's OpenAI-compatible API for tool calls.
"""

import asyncio
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

    async def chat(self, system: str, messages: list[dict], tools: list[dict] | None = None,
                   model: str | None = None) -> AdapterResponse:
        """Send a message to OpenRouter, returns an AdapterResponse. `model`
        overrides config.MODEL for this one call (used by per-step model picks)."""
        # Build messages with system prompt first
        api_messages = [{"role": "system", "content": system}] + messages

        payload = {
            "model": model or config.MODEL,
            "max_tokens": config.MAX_RESPONSE_TOKENS,
            "messages": api_messages,
            # Ask OpenRouter for full usage accounting (cached tokens + real cost).
            "usage": {"include": True},
        }
        # Prefer providers with working prompt caching: a KV cache is
        # provider-local, so OpenRouter's default load-balancing would land
        # request N+1 on a different provider and miss the cache.
        # Fallbacks stay enabled — availability beats cache savings.
        # Pin the provider order for THIS model (pins are model-specific — see
        # config.MODEL_PROVIDER_PINS). Falls back to the global order, then to
        # default routing. Read fresh each call so a live MODEL switch retargets.
        model_id = model or config.MODEL
        pins = getattr(config, "MODEL_PROVIDER_PINS", {}) or {}
        order = pins.get(model_id) or getattr(config, "OPENROUTER_PROVIDER_ORDER", None)
        provider = {"order": order, "allow_fallbacks": True} if order else {}
        if tools:
            payload["tools"] = tools
            # Some providers serve our model without tool-calling support. Ask
            # OpenRouter to consider only providers honoring every parameter we
            # send, so a pin or fallback can't land us somewhere that ignores
            # `tools` and answers in prose instead of calling one.
            provider["require_parameters"] = True
        if provider:
            payload["provider"] = provider

        # OpenRouter occasionally returns a 200 with a non-JSON body (gateway
        # hiccups, more likely on large generations), which used to surface as a
        # cryptic bare JSONDecodeError from resp.json(). Retry transient failures,
        # then fail loudly with the actual response body so it's debuggable.
        resp = None
        for attempt in range(3):
            try:
                resp = await self._client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                break
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                if attempt < 2:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                body = resp.text[:300] if resp is not None else ""
                raise RuntimeError(
                    f"LLM request failed after 3 attempts ({type(e).__name__}: {e})"
                    + (f" — response body: {body!r}" if body else "")
                ) from e

        choice = data["choices"][0]
        message = choice["message"]

        # Parse text
        text = message.get("content")

        # Map finish reason
        finish = choice.get("finish_reason", "stop")
        stop_reason = "tool_use" if finish == "tool_calls" else "end_turn"
        truncated = finish == "length"

        # Parse tool calls
        tool_calls = []
        for tc in message.get("tool_calls") or []:
            func = tc["function"]
            args = func.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError as e:
                    hint = " (response was cut off by max_tokens — raise MAX_RESPONSE_TOKENS)" if truncated else ""
                    args = {
                        "__parse_error__": f"{type(e).__name__}: {e}{hint}",
                        "__raw_arguments__": args,
                    }
            tool_calls.append(ToolCall(
                id=tc["id"],
                name=func["name"],
                arguments=args,
            ))

        # Parse usage (usage accounting adds cached-token detail + real cost)
        usage_data = data.get("usage", {})
        prompt_details = usage_data.get("prompt_tokens_details") or {}

        return AdapterResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            raw_message=message,
            usage=Usage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                cached_input_tokens=prompt_details.get("cached_tokens", 0) or 0,
                cost_usd=float(usage_data.get("cost") or 0.0),
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
