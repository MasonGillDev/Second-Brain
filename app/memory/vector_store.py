"""
ChromaDB-backed vector store for persistent memory.

Manages four collections:
  - long_term: Facts, knowledge, user preferences
  - episodic: Summarized interaction episodes with outcomes
  - procedural: How-to knowledge and task procedures
  - documents: Ingested markdown files from ./memory/docs/
"""

import time
import chromadb
import config

CHROMA_HOST = "127.0.0.1"
CHROMA_PORT = 8000


def _connect_with_retry(host: str, port: int, attempts: int = 30, delay: float = 1.0):
    """Connect to the chromadb HTTP server, retrying so launchd start-order doesn't matter."""
    last_err = None
    for _ in range(attempts):
        try:
            client = chromadb.HttpClient(host=host, port=port)
            client.heartbeat()
            return client
        except Exception as e:
            last_err = e
            time.sleep(delay)
    raise RuntimeError(f"Could not reach chromadb at {host}:{port} after {attempts} attempts: {last_err}")


class VectorStore:
    def __init__(self):
        self._client = _connect_with_retry(CHROMA_HOST, CHROMA_PORT)
        self.collections = {
            "long_term": self._client.get_or_create_collection(
                name="long_term",
                metadata={"description": "Persistent facts, knowledge, user preferences"},
            ),
            "episodic": self._client.get_or_create_collection(
                name="episodic",
                metadata={"description": "Summarized interaction episodes"},
            ),
            "procedural": self._client.get_or_create_collection(
                name="procedural",
                metadata={"description": "Task procedures and how-to knowledge"},
            ),
            "documents": self._client.get_or_create_collection(
                name="documents",
                metadata={"description": "Ingested markdown documents"},
            ),
            "reference": self._client.get_or_create_collection(
                name="reference",
                metadata={"description": "Reference-tier memories: useful but not daily"},
            ),
            "archive": self._client.get_or_create_collection(
                name="archive",
                metadata={"description": "Archived memories: outdated or rarely needed"},
            ),
            "code_context": self._client.get_or_create_collection(
                name="code_context",
                metadata={"description": "Code comments, docstrings, and signatures"},
            ),
        }

    def add(self, collection_name: str, text: str, metadata: dict | None = None, doc_id: str | None = None):
        """Add a memory to a collection."""
        collection = self.collections[collection_name]
        doc_id = doc_id or f"{collection_name}_{int(time.time() * 1000)}"
        meta = metadata or {}
        meta["created_at"] = time.time()
        meta["last_accessed"] = 0.0
        meta["access_count"] = 0

        collection.add(
            documents=[text],
            metadatas=[meta],
            ids=[doc_id],
        )
        return doc_id

    def add_batch(self, collection_name: str, texts: list[str], metadatas: list[dict] | None = None, ids: list[str] | None = None):
        """Add multiple memories at once."""
        collection = self.collections[collection_name]
        now = time.time()

        if ids is None:
            ids = [f"{collection_name}_{int(now * 1000)}_{i}" for i in range(len(texts))]

        if metadatas is None:
            metadatas = [{"created_at": now} for _ in texts]
        else:
            for m in metadatas:
                m["created_at"] = now

        collection.add(documents=texts, metadatas=metadatas, ids=ids)

    def query(self, collection_name: str, query_text: str, top_k: int = 3, where: dict | None = None,
              min_relevance: float | None = None) -> list[dict]:
        """Query a collection for relevant memories.

        min_relevance: per-call override of the relevance floor. Defaults to
        config.RETRIEVAL_MIN_RELEVANCE. Pass a lower value (e.g. for procedural
        memories) to admit looser semantic matches.
        """
        collection = self.collections[collection_name]

        if collection.count() == 0:
            return []

        threshold = min_relevance if min_relevance is not None else config.RETRIEVAL_MIN_RELEVANCE

        kwargs = {
            "query_texts": [query_text],
            "n_results": min(top_k, collection.count()),
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        memories = []
        ids_to_update = []
        metas_to_update = []
        now = time.time()

        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i] if results["distances"] else 0
            # ChromaDB returns L2 distance; convert to 0-1 relevance score
            relevance = 1 / (1 + distance)

            if relevance < threshold:
                continue

            doc_id = results["ids"][0][i]
            meta = (results["metadatas"][0][i] if results["metadatas"] else {}) or {}

            # Track access
            access_count = meta.get("access_count", 0) + 1
            updated_meta = {**meta, "last_accessed": now, "access_count": access_count}

            ids_to_update.append(doc_id)
            metas_to_update.append(updated_meta)

            memories.append({
                "id": doc_id,
                "text": results["documents"][0][i],
                "metadata": updated_meta,
                "relevance": round(relevance, 3),
                "access_count": access_count,
            })

        # Batch update access metadata
        if ids_to_update:
            try:
                collection.update(ids=ids_to_update, metadatas=metas_to_update)
            except Exception:
                pass  # Don't fail queries over tracking errors

        return memories

    def delete(self, collection_name: str, doc_id: str):
        """Delete a memory by ID."""
        self.collections[collection_name].delete(ids=[doc_id])

    def delete_by_metadata(self, collection_name: str, where: dict):
        """Delete memories matching metadata filter."""
        collection = self.collections[collection_name]
        # Query to find matching IDs, then delete them
        results = collection.get(where=where)
        if results["ids"]:
            collection.delete(ids=results["ids"])

    def get_all(self, collection_name: str, limit: int = 100) -> list[dict]:
        """Get all memories from a collection (up to limit)."""
        collection = self.collections[collection_name]
        if collection.count() == 0:
            return []
        results = collection.get(limit=min(limit, collection.count()))
        memories = []
        for i in range(len(results["ids"])):
            memories.append({
                "id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i] or {},
            })
        return memories

    def count(self, collection_name: str) -> int:
        return self.collections[collection_name].count()

    def get_stats(self) -> dict:
        return {name: col.count() for name, col in self.collections.items()}
