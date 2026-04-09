"""
Memory Maintenance — deduplication and consolidation.

Uses Haiku (SUMMARIZATION_MODEL) to keep long-term memory clean:
  - dedup_and_store(): Gates every write — STORE, MERGE, or SKIP
  - consolidate(): Periodic batch merge of related memories
"""

import json
import time
import anthropic
import config
from memory.vector_store import VectorStore


# ---------------------------------------------------------------------------
# Prompts (kept minimal for Haiku cost)
# ---------------------------------------------------------------------------

DEDUP_PROMPT = """Given a NEW memory and EXISTING memories, decide what to do.

NEW: {new_text}

EXISTING:
{existing_list}

Reply with exactly one JSON object, no other text:
- {{"action": "SKIP"}} — NEW is already covered by an existing memory
- {{"action": "STORE"}} — NEW contains genuinely different information
- {{"action": "MERGE", "merge_with": <number>, "merged_text": "..."}} — NEW updates/extends an existing memory. merged_text combines both into one concise fact."""

CONSOLIDATION_PROMPT = """Merge these related memories into ONE concise memory that preserves all unique information.

Memories:
{memory_list}

Reply with exactly one JSON object, no other text:
{{"merged": "single consolidated fact"}}
If they are actually unrelated, reply: {{"merged": null}}"""


class MemoryMaintenance:
    def __init__(self, vector_store: VectorStore, llm_client: anthropic.Anthropic):
        self.vector_store = vector_store
        self._llm = llm_client

    # ------------------------------------------------------------------
    # Dedup on Write
    # ------------------------------------------------------------------

    def dedup_and_store(self, collection_name: str, text: str, metadata: dict | None = None) -> dict:
        """
        Smart memory storage: checks for duplicates before writing.

        Returns: {"action": "STORE"|"MERGE"|"SKIP", "id": str|None}
        """
        metadata = metadata or {}

        # Query for similar existing memories
        similar = self.vector_store.query(
            collection_name, text, top_k=config.DEDUP_TOP_K
        )

        # Filter to those above relevance threshold
        similar = [m for m in similar if m["relevance"] >= config.DEDUP_MIN_RELEVANCE]

        # No similar memories — store directly
        if not similar:
            doc_id = self.vector_store.add(collection_name, text, metadata)
            return {"action": "STORE", "id": doc_id}

        # Ask Haiku what to do
        existing_list = "\n".join(
            f"{i+1}. {m['text']}" for i, m in enumerate(similar)
        )
        prompt = DEDUP_PROMPT.format(new_text=text, existing_list=existing_list)

        try:
            response = self._llm.messages.create(
                model=config.SUMMARIZATION_MODEL,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            decision = self._parse_json(raw)

            if not decision or "action" not in decision:
                # Parse failed — safe default: store it
                doc_id = self.vector_store.add(collection_name, text, metadata)
                return {"action": "STORE", "id": doc_id}

            action = decision["action"].upper()

            if action == "SKIP":
                if config.LOG_TOKEN_USAGE:
                    print(f"  [dedup] Skipped (already known): {text[:60]}")
                return {"action": "SKIP", "id": None}

            elif action == "MERGE":
                merge_idx = decision.get("merge_with", 1) - 1  # 1-based → 0-based
                merged_text = decision.get("merged_text", text)

                if 0 <= merge_idx < len(similar):
                    old_id = similar[merge_idx]["id"]
                    old_meta = similar[merge_idx]["metadata"]

                    # Preserve the higher access count and original creation time
                    metadata["access_count"] = max(
                        old_meta.get("access_count", 0),
                        metadata.get("access_count", 0),
                    )
                    metadata["type"] = "merged"

                    # Delete old, store merged
                    self.vector_store.delete(collection_name, old_id)
                    doc_id = self.vector_store.add(collection_name, merged_text, metadata)

                    if config.LOG_TOKEN_USAGE:
                        print(f"  [dedup] Merged: {merged_text[:60]}")
                    return {"action": "MERGE", "id": doc_id}
                else:
                    # Invalid index — fall through to store
                    doc_id = self.vector_store.add(collection_name, text, metadata)
                    return {"action": "STORE", "id": doc_id}

            else:  # STORE or unknown
                doc_id = self.vector_store.add(collection_name, text, metadata)
                return {"action": "STORE", "id": doc_id}

        except Exception as e:
            if config.LOG_TOKEN_USAGE:
                print(f"  [dedup] Error, storing anyway: {e}")
            doc_id = self.vector_store.add(collection_name, text, metadata)
            return {"action": "STORE", "id": doc_id}

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    def consolidate(self, collection_name: str = "long_term") -> dict:
        """
        Merge related memories into stronger single entries.

        Returns: {"clusters_found": N, "memories_before": X, "memories_after": Y}
        """
        all_memories = self.vector_store.get_all(
            collection_name, limit=config.CONSOLIDATION_BATCH_LIMIT
        )
        memories_before = len(all_memories)

        if memories_before <= 1:
            return {"clusters_found": 0, "memories_before": memories_before, "memories_after": memories_before}

        # Build clusters using vector similarity
        clusters = self._find_clusters(collection_name, all_memories)

        if not clusters:
            return {"clusters_found": 0, "memories_before": memories_before, "memories_after": memories_before}

        # Merge each cluster
        deleted_count = 0
        created_count = 0

        for cluster in clusters:
            merged = self._merge_cluster(collection_name, cluster)
            if merged:
                deleted_count += len(cluster)
                created_count += 1

        memories_after = memories_before - deleted_count + created_count

        return {
            "clusters_found": len(clusters),
            "memories_before": memories_before,
            "memories_after": memories_after,
        }

    def _find_clusters(self, collection_name: str, memories: list[dict]) -> list[list[dict]]:
        """Group related memories using vector similarity (no LLM calls)."""
        # Build adjacency via vector queries
        id_to_mem = {m["id"]: m for m in memories}
        adjacency: dict[str, set[str]] = {m["id"]: set() for m in memories}

        for mem in memories:
            similar = self.vector_store.query(
                collection_name, mem["text"], top_k=5
            )
            for s in similar:
                if s["id"] != mem["id"] and s["relevance"] >= config.CONSOLIDATION_SIMILARITY_THRESHOLD:
                    adjacency[mem["id"]].add(s["id"])
                    if s["id"] in adjacency:
                        adjacency[s["id"]].add(mem["id"])

        # Union-find to get connected components
        visited = set()
        clusters = []

        for mem_id in adjacency:
            if mem_id in visited:
                continue

            # BFS to find connected component
            component = []
            queue = [mem_id]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                if current in id_to_mem:
                    component.append(id_to_mem[current])
                for neighbor in adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)

            # Only keep clusters of 2+ memories, capped at max size
            if len(component) >= 2:
                # If too large, take the most connected subset
                if len(component) > config.CONSOLIDATION_MAX_CLUSTER_SIZE:
                    component = component[:config.CONSOLIDATION_MAX_CLUSTER_SIZE]
                clusters.append(component)

        return clusters

    def _merge_cluster(self, collection_name: str, cluster: list[dict]) -> bool:
        """Use Haiku to merge a cluster of related memories. Returns True if merged."""
        memory_list = "\n".join(
            f"{i+1}. {m['text']}" for i, m in enumerate(cluster)
        )
        prompt = CONSOLIDATION_PROMPT.format(memory_list=memory_list)

        try:
            response = self._llm.messages.create(
                model=config.SUMMARIZATION_MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            result = self._parse_json(raw)

            if not result or result.get("merged") is None:
                return False  # Haiku says they're unrelated — leave them

            merged_text = result["merged"]

            # Build metadata for consolidated memory
            # Use most common category, highest access count, original creation time
            categories = [m["metadata"].get("category", "general") for m in cluster]
            most_common_category = max(set(categories), key=categories.count)
            max_access = max(m["metadata"].get("access_count", 0) for m in cluster)
            earliest_created = min(m["metadata"].get("created_at", time.time()) for m in cluster)
            original_ids = [m["id"] for m in cluster]

            # Delete originals
            for mem in cluster:
                self.vector_store.delete(collection_name, mem["id"])

            # Store consolidated version
            self.vector_store.add(collection_name, merged_text, {
                "type": "consolidated",
                "category": most_common_category,
                "access_count": max_access,
                "created_at": earliest_created,
                "consolidated_from": ",".join(original_ids),
            })

            if config.LOG_TOKEN_USAGE:
                print(f"  [consolidate] Merged {len(cluster)} → 1: {merged_text[:60]}")

            return True

        except Exception as e:
            if config.LOG_TOKEN_USAGE:
                print(f"  [consolidate] Merge failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """Extract and parse the first JSON object from text."""
        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        # Find first { ... }
        brace_start = text.find("{")
        if brace_start == -1:
            return None

        # Find matching closing brace
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start:i+1])
                    except json.JSONDecodeError:
                        return None
        return None
