"""
Sleep Agent Tools.

In-process tool functions for the sleep agent. No MCP needed — these
operate directly on VectorStore. Each function returns a string result.

Also exports TOOL_DEFINITIONS for the Claude API tool-use format.
"""

import time
from memory.vector_store import VectorStore
from memory.recursive_search import TIER_MAP


def _resolve_collection(tier: str) -> str:
    """Convert tier name to collection name."""
    collection = TIER_MAP.get(tier)
    if not collection:
        raise ValueError(f"Unknown tier '{tier}'. Use: {', '.join(TIER_MAP.keys())}")
    return collection


def search_memories(vs: VectorStore, query: str, tier: str = "all", top_k: int = 10) -> str:
    """Search memories by similarity."""
    results = []

    tiers_to_search = TIER_MAP.keys() if tier == "all" else [tier]

    for t in tiers_to_search:
        collection = _resolve_collection(t)
        if vs.collections[collection].count() == 0:
            continue
        hits = vs.query(collection, query, top_k=top_k)
        for h in hits:
            results.append(f"[{h['id']}] (tier: {t}, rel: {h['relevance']}) {h['text']}")

    return "\n".join(results) if results else "No results found."


def update_memory(vs: VectorStore, memory_id: str, tier: str, new_text: str) -> str:
    """Rewrite a memory's text in-place."""
    collection = _resolve_collection(tier)
    coll = vs.collections[collection]

    # Get existing memory
    existing = coll.get(ids=[memory_id])
    if not existing["ids"]:
        return f"Memory {memory_id} not found in {tier}."

    metadata = existing["metadatas"][0] or {}
    metadata["last_modified"] = time.time()

    # Delete and re-add (ChromaDB doesn't support text update directly)
    coll.delete(ids=[memory_id])
    coll.add(documents=[new_text], metadatas=[metadata], ids=[memory_id])

    return f"Updated {memory_id} in {tier}."


def split_memory(vs: VectorStore, memory_id: str, tier: str, new_memories: list[dict]) -> str:
    """Delete one memory, create N focused entries."""
    collection = _resolve_collection(tier)
    coll = vs.collections[collection]

    # Get original
    existing = coll.get(ids=[memory_id])
    if not existing["ids"]:
        return f"Memory {memory_id} not found in {tier}."

    original_meta = existing["metadatas"][0] or {}
    created_at = original_meta.get("created_at", time.time())
    access_count = original_meta.get("access_count", 0)

    # Delete original
    coll.delete(ids=[memory_id])

    # Create new entries
    created_ids = []
    for i, mem in enumerate(new_memories):
        new_id = f"{collection}_{int(time.time() * 1000)}_{i}"
        meta = {
            "category": mem.get("category", original_meta.get("category", "general")),
            "type": "split",
            "split_from": memory_id,
            "created_at": created_at,
            "last_accessed": 0.0,
            "access_count": access_count,
        }
        coll.add(documents=[mem["text"]], metadatas=[meta], ids=[new_id])
        created_ids.append(new_id)

    return f"Split {memory_id} into {len(created_ids)} memories: {', '.join(created_ids)}"


def merge_memories(vs: VectorStore, memory_ids: list[str], tiers: list[str],
                   merged_text: str, target_tier: str) -> str:
    """Delete N memories, create one merged entry."""
    if len(memory_ids) != len(tiers):
        return "memory_ids and tiers must be the same length."

    earliest_created = time.time()
    max_access = 0
    source_ids = []

    # Delete all source memories
    for mem_id, tier in zip(memory_ids, tiers):
        collection = _resolve_collection(tier)
        coll = vs.collections[collection]

        existing = coll.get(ids=[mem_id])
        if existing["ids"]:
            meta = existing["metadatas"][0] or {}
            earliest_created = min(earliest_created, meta.get("created_at", time.time()))
            max_access = max(max_access, meta.get("access_count", 0))
            coll.delete(ids=[mem_id])
            source_ids.append(mem_id)

    if not source_ids:
        return "None of the specified memories were found."

    # Create merged entry
    target_collection = _resolve_collection(target_tier)
    new_id = f"{target_collection}_{int(time.time() * 1000)}"
    meta = {
        "type": "merged",
        "merged_from": ",".join(source_ids),
        "created_at": earliest_created,
        "last_accessed": 0.0,
        "access_count": max_access,
        "category": "general",
    }
    vs.collections[target_collection].add(documents=[merged_text], metadatas=[meta], ids=[new_id])

    return f"Merged {len(source_ids)} memories into {new_id} in {target_tier}."


def move_memory(vs: VectorStore, memory_id: str, from_tier: str, to_tier: str) -> str:
    """Move a memory between tier collections."""
    from_collection = _resolve_collection(from_tier)
    to_collection = _resolve_collection(to_tier)

    # Read from source
    coll = vs.collections[from_collection]
    existing = coll.get(ids=[memory_id])
    if not existing["ids"]:
        return f"Memory {memory_id} not found in {from_tier}."

    text = existing["documents"][0]
    metadata = existing["metadatas"][0] or {}

    # Delete from source
    coll.delete(ids=[memory_id])

    # Add to target
    new_id = f"{to_collection}_{int(time.time() * 1000)}"
    metadata["moved_from"] = from_tier
    vs.collections[to_collection].add(documents=[text], metadatas=[metadata], ids=[new_id])

    return f"Moved {memory_id} from {from_tier} to {to_tier} (new id: {new_id})."


def tag_memory(vs: VectorStore, memory_id: str, tier: str, category: str) -> str:
    """Update a memory's category metadata."""
    collection = _resolve_collection(tier)
    coll = vs.collections[collection]

    existing = coll.get(ids=[memory_id])
    if not existing["ids"]:
        return f"Memory {memory_id} not found in {tier}."

    metadata = existing["metadatas"][0] or {}
    metadata["category"] = category

    coll.update(ids=[memory_id], metadatas=[metadata])

    return f"Tagged {memory_id} as '{category}'."


# Tool dispatcher — maps tool names to functions
TOOL_FUNCTIONS = {
    "search_memories": search_memories,
    "update_memory": update_memory,
    "split_memory": split_memory,
    "merge_memories": merge_memories,
    "move_memory": move_memory,
    "tag_memory": tag_memory,
}

# Tool definitions for Claude API
TOOL_DEFINITIONS = [
    {
        "name": "search_memories",
        "description": "Search memories by similarity across one or all tiers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search for."},
                "tier": {"type": "string", "enum": ["active", "reference", "archive", "all"], "default": "all"},
                "top_k": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "update_memory",
        "description": "Rewrite a memory's text. Use to improve clarity or fix wording.",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string"},
                "tier": {"type": "string", "enum": ["active", "reference", "archive"]},
                "new_text": {"type": "string", "description": "The improved text."},
            },
            "required": ["memory_id", "tier", "new_text"],
        },
    },
    {
        "name": "split_memory",
        "description": "Split a bloated memory into multiple focused entries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string"},
                "tier": {"type": "string", "enum": ["active", "reference", "archive"]},
                "new_memories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "category": {"type": "string"},
                        },
                        "required": ["text"],
                    },
                },
            },
            "required": ["memory_id", "tier", "new_memories"],
        },
    },
    {
        "name": "merge_memories",
        "description": "Merge duplicate or overlapping memories into one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_ids": {"type": "array", "items": {"type": "string"}},
                "tiers": {"type": "array", "items": {"type": "string", "enum": ["active", "reference", "archive"]}},
                "merged_text": {"type": "string"},
                "target_tier": {"type": "string", "enum": ["active", "reference", "archive"]},
            },
            "required": ["memory_ids", "tiers", "merged_text", "target_tier"],
        },
    },
    {
        "name": "move_memory",
        "description": "Move a memory between tiers (active/reference/archive).",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string"},
                "from_tier": {"type": "string", "enum": ["active", "reference", "archive"]},
                "to_tier": {"type": "string", "enum": ["active", "reference", "archive"]},
            },
            "required": ["memory_id", "from_tier", "to_tier"],
        },
    },
    {
        "name": "tag_memory",
        "description": "Update a memory's category for better retrieval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string"},
                "tier": {"type": "string", "enum": ["active", "reference", "archive"]},
                "category": {"type": "string", "description": "e.g., user_fact, preference, project_context, decision"},
            },
            "required": ["memory_id", "tier", "category"],
        },
    },
    {
        "name": "done",
        "description": "Signal that you are finished reorganizing. Include a summary of what you did.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Brief summary of actions taken."},
            },
            "required": ["summary"],
        },
    },
]
