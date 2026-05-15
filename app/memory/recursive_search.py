"""
Recursive Similarity Search.

Starting from seed memories (created/modified today), performs a breadth-first
search through similarity space with decay per depth level. Returns a capped,
deduplicated batch of related memories for the sleep agent to process.
"""

import time
import config
from collections import deque
from memory.vector_store import VectorStore


# Tier name -> collection name mapping (writable tiers)
TIER_MAP = {
    "active": "long_term",
    "reference": "reference",
    "archive": "archive",
}

# Read-only collections included in search for context
CONTEXT_COLLECTIONS = {
    "documents": "documents",
}

COLLECTION_TO_TIER = {v: k for k, v in TIER_MAP.items()}
COLLECTION_TO_TIER.update({v: k for k, v in CONTEXT_COLLECTIONS.items()})

# All collections to search through
ALL_SEARCH_COLLECTIONS = {**TIER_MAP, **CONTEXT_COLLECTIONS}


def _get_seeds(vector_store: VectorStore, lookback_hours: int, max_seeds: int) -> list[dict]:
    """Get seed memories: recently created or modified."""
    cutoff = time.time() - (lookback_hours * 3600)

    all_memories = vector_store.get_all("long_term", limit=200)

    # Filter to memories created within lookback window
    seeds = [
        m for m in all_memories
        if m["metadata"].get("created_at", 0) >= cutoff
    ]

    # Sort by creation time, most recent first
    seeds.sort(key=lambda m: m["metadata"].get("created_at", 0), reverse=True)

    # Fallback: if no new memories, use most recently accessed
    if not seeds:
        seeds = sorted(
            all_memories,
            key=lambda m: m["metadata"].get("last_accessed", 0),
            reverse=True,
        )

    return seeds[:max_seeds]


def recursive_similarity_search(
    vector_store: VectorStore,
    search_depth: int | None = None,
    similarity_decay: float | None = None,
    top_k_per_hop: int | None = None,
    min_relevance: float | None = None,
    max_total: int | None = None,
    seed_lookback_hours: int | None = None,
    max_seeds: int | None = None,
) -> list[dict]:
    """
    Build a batch of related memories starting from today's seeds.

    Returns a list of dicts:
        {id, text, metadata, effective_relevance, tier, depth}
    """
    # Use config defaults
    search_depth = search_depth or config.SLEEP_SEARCH_DEPTH
    similarity_decay = similarity_decay or config.SLEEP_SIMILARITY_DECAY
    top_k_per_hop = top_k_per_hop or config.SLEEP_TOP_K_PER_HOP
    min_relevance = min_relevance or config.SLEEP_MIN_RELEVANCE
    max_total = max_total or config.SLEEP_MAX_CONTEXT_MEMORIES
    seed_lookback_hours = seed_lookback_hours or config.SLEEP_SEED_LOOKBACK_HOURS
    max_seeds = max_seeds or config.SLEEP_MAX_SEEDS

    # Phase 1: Seed selection
    seeds = _get_seeds(vector_store, seed_lookback_hours, max_seeds)
    if not seeds:
        return []

    # Phase 2: BFS expansion
    # seen maps memory_id -> {best effective_relevance, depth, tier, text, metadata}
    seen: dict[str, dict] = {}

    # Initialize with seeds
    queue = deque()
    for seed in seeds:
        seen[seed["id"]] = {
            "id": seed["id"],
            "text": seed["text"],
            "metadata": seed["metadata"],
            "effective_relevance": 1.0,
            "tier": "active",
            "depth": 0,
        }
        queue.append((seed["text"], 0))

    # BFS through similarity space
    while queue:
        query_text, current_depth = queue.popleft()

        if current_depth >= search_depth:
            continue

        next_depth = current_depth + 1
        decay_factor = similarity_decay ** next_depth

        # Search across all collections (tiers + read-only context)
        for tier_name, collection_name in ALL_SEARCH_COLLECTIONS.items():
            if collection_name not in vector_store.collections:
                continue
            if vector_store.collections[collection_name].count() == 0:
                continue

            results = vector_store.query(
                collection_name,
                query_text,
                top_k=top_k_per_hop,
            )

            for result in results:
                effective_rel = result["relevance"] * decay_factor

                if effective_rel < min_relevance:
                    continue

                # Higher bar for document memories
                is_document = tier_name in CONTEXT_COLLECTIONS
                if is_document and effective_rel < config.SLEEP_MIN_DOCUMENT_RELEVANCE:
                    continue

                mem_id = result["id"]

                # Keep the path with highest effective relevance
                if mem_id in seen and seen[mem_id]["effective_relevance"] >= effective_rel:
                    continue

                seen[mem_id] = {
                    "id": mem_id,
                    "text": result["text"],
                    "metadata": result["metadata"],
                    "effective_relevance": round(effective_rel, 3),
                    "tier": tier_name,
                    "depth": next_depth,
                }

                # Continue searching from this result
                queue.append((result["text"], next_depth))

    # Phase 3: Cap and return
    # Separate memories from read-only documents
    memories = [m for m in seen.values() if m["tier"] not in CONTEXT_COLLECTIONS]
    documents = [m for m in seen.values() if m["tier"] in CONTEXT_COLLECTIONS]

    # Sort each by relevance
    memories.sort(key=lambda m: m["effective_relevance"], reverse=True)
    documents.sort(key=lambda m: m["effective_relevance"], reverse=True)

    # Cap documents separately
    max_docs = getattr(config, "SLEEP_MAX_DOCUMENT_MEMORIES", 5)
    documents = documents[:max_docs]

    # Combine and cap total
    batch = memories + documents
    return batch[:max_total]
