"""
Memory MCP Server.

Gives the agent real tools to store and search its own long-term memory.
"""

import time
import chromadb
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("memory")

CHROMA_DIR = "./memory/data/chroma"
_client = chromadb.PersistentClient(path=CHROMA_DIR)
_collection = _client.get_or_create_collection(name="long_term")


@mcp.tool()
def store_memory(text: str, category: str = "general") -> str:
    """
    Store a fact in long-term memory. ONLY use this when the user explicitly
    asks you to remember something. Do not store casual conversation details.

    Args:
        text: The fact to store. Must be concise and standalone.
              Good: "Mason prefers Go for backend development"
              Bad: "The user said they like Go"
        category: One of: user_fact, preference, decision, project_context, general
    """
    doc_id = f"long_term_{int(time.time() * 1000)}"
    _collection.add(
        documents=[text],
        metadatas=[{"type": "agent_stored", "category": category, "created_at": time.time()}],
        ids=[doc_id],
    )
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
    if _collection.count() == 0:
        return "No memories stored yet."

    results = _collection.query(
        query_texts=[query],
        n_results=min(top_k, _collection.count()),
    )

    if not results["ids"][0]:
        return "No relevant memories found."

    lines = []
    for i, (doc_id, text, meta) in enumerate(zip(
        results["ids"][0], results["documents"][0], results["metadatas"][0]
    )):
        category = meta.get("category", "")
        lines.append(f"- ({category}) {text}")

    return "\n".join(lines)


@mcp.tool()
def list_all_memories() -> str:
    """List all stored long-term memories. Use when the user asks what you remember about them."""
    if _collection.count() == 0:
        return "No memories stored yet."

    results = _collection.get(limit=50)
    lines = [f"Long-term memories ({_collection.count()} total):\n"]
    for doc_id, text, meta in zip(
        results["ids"], results["documents"], results["metadatas"]
    ):
        category = meta.get("category", "")
        lines.append(f"- [{doc_id}] ({category}) {text}")

    return "\n".join(lines)


@mcp.tool()
def delete_memory(memory_id: str) -> str:
    """
    Delete a specific memory by its ID.

    Args:
        memory_id: The ID of the memory to delete (from list_all_memories).
    """
    try:
        _collection.delete(ids=[memory_id])
        return f"Deleted memory {memory_id}"
    except Exception as e:
        return f"Error deleting memory: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
