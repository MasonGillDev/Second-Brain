"""
Abstract LLM adapter interface.

Defines the contract that all provider adapters must implement.
This keeps the agent loop completely provider-agnostic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A single tool call requested by the model."""
    id: str             # Provider-assigned ID (needed to pair with results)
    name: str           # Namespaced tool name (e.g., "filesystem__read_file")
    arguments: dict     # Parsed arguments


@dataclass
class Usage:
    """Token usage for a single API call."""
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass
class AdapterResponse:
    """Standardized response from any LLM provider."""
    text: str | None                    # Assistant text (None if only tool calls)
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"       # "end_turn" or "tool_use"
    raw_message: Any = None             # Full provider response (for message history)
    usage: Usage = field(default_factory=Usage)


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters."""

    @abstractmethod
    def format_tools(self, tools: list[dict]) -> Any:
        """
        Convert provider-agnostic tool definitions to the provider's API format.
        Input: [{"name": ..., "description": ..., "input_schema": {...}}]
        Output: provider-specific format
        """

    @abstractmethod
    async def chat(self, system: str, messages: list[dict], tools: Any = None) -> AdapterResponse:
        """
        Send a message to the LLM. Returns an AdapterResponse.
        The messages list uses the provider's native format.
        """

    @abstractmethod
    def format_assistant_message(self, raw_message: Any) -> dict:
        """
        Convert the raw API response into a message dict that can be
        appended to the messages list for the next turn.
        """

    @abstractmethod
    def format_tool_results(self, results: list[tuple[str, str]]) -> dict:
        """
        Format tool results as a message to send back to the model.
        Input: [(tool_call_id, result_text), ...]
        Output: provider-specific message dict
        """
