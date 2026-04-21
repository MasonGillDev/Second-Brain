"""
Memory MCP Server.

Gives the agent real tools to store and search its own long-term memory.
Uses MemoryMaintenance for dedup on write.
"""

import sys
import os

# Add project root to path so we can import memory modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
import config
from keychain import get_secret
from mcp.server.fastmcp import FastMCP
from memory.vector_store import VectorStore
from memory.maintenance import MemoryMaintenance

mcp = FastMCP("memory")

_vector_store = VectorStore()
_maintenance = MemoryMaintenance(_vector_store, anthropic.Anthropic(api_key=get_secret("anthropic-api-key")))


@mcp.tool()
def store_memory(text: str, category: str = "general") -> str:
    """
    Store a fact in long-term memory. ONLY use this when the user explicitly
    asks you to remember something. Do not store casual conversation details.

    Args:
        text: The fact to store. Must be concise and standalone.
              Good: "Mason prefers Go for backend development"
              Bad: "The user said they like Go"
        category: Common categories: user_fact, preference, decision, project_context, general.
                  You can also create custom categories as needed (e.g., "recipe", "health", "finance").
    """
    result = _maintenance.dedup_and_store("long_term", text, {
        "type": "agent_stored",
        "category": category,
    })

    if result["action"] == "SKIP":
        return f"Already known: {text}"
    elif result["action"] == "MERGE":
        return f"Updated existing memory with: {text}"
    else:
        return f"Stored: {text}"


@mcp.tool()
def search_memory(query: str, top_k: int = 5) -> str:
    """
    Search long-term memory for relevant information.
    Use this when you need to recall something about the user or past conversations.

    Args:
        query: What to search for (e.g., "user's name", "programming preferences").
        top_k: Maximum number of results to return (default 5).
    """
    results = _vector_store.query("long_term", query, top_k=top_k)

    if not results:
        return "No relevant memories found."

    lines = []
    for mem in results:
        meta = mem.get("metadata") or {}
        category = meta.get("category", "")
        lines.append(f"- ({category}) {mem['text']}")

    return "\n".join(lines)


@mcp.tool()
def list_all_memories() -> str:
    """List all stored long-term memories. Use when the user asks what you remember about them."""
    all_memories = _vector_store.get_all("long_term", limit=50)

    if not all_memories:
        return "No memories stored yet."

    lines = [f"Long-term memories ({len(all_memories)} total):\n"]
    for mem in all_memories:
        category = mem["metadata"].get("category", "")
        lines.append(f"- [{mem['id']}] ({category}) {mem['text']}")

    return "\n".join(lines)


@mcp.tool()
def delete_memory(memory_id: str) -> str:
    """
    Delete a specific memory by its ID.

    Args:
        memory_id: The ID of the memory to delete (from list_all_memories).
    """
    try:
        _vector_store.delete("long_term", memory_id)
        return f"Deleted memory {memory_id}"
    except Exception as e:
        return f"Error deleting memory: {e}"


@mcp.tool()
def update_personality(personality: str) -> str:
    """
    Replace your personality/voice description with a new version.
    This text is injected into your system prompt and shapes how you communicate.

    ALWAYS call get_personality first, then revise and write the full updated text.
    Do not discard traits that are still relevant — merge old and new.

    Focus on tone, style, and behavioral traits.
    Example: "Direct and dry. Uses analogies. Skips filler. Matches the user's energy."

    Args:
        personality: The complete personality text (replaces current entirely).
    """
    max_chars = getattr(config, "PERSONALITY_MAX_CHARS", 500)

    if len(personality) > max_chars:
        return f"Too long ({len(personality)} chars). Max is {max_chars}. Shorten and try again."

    path = config.PERSONALITY_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        f.write(personality)

    return f"Personality updated ({len(personality)}/{max_chars} chars)."


@mcp.tool()
def get_personality() -> str:
    """Read the current personality description. Always check this before calling update_personality."""
    path = config.PERSONALITY_FILE
    if not os.path.exists(path):
        return "(No personality set yet.)"
    with open(path) as f:
        return f.read().strip() or "(Empty.)"


if __name__ == "__main__":
    mcp.run(transport="stdio")
