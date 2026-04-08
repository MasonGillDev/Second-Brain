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


class VectorStore:
    def __init__(self):
        self._client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
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

    def query(self, collection_name: str, query_text: str, top_k: int = 3, where: dict | None = None) -> list[dict]:
        """Query a collection for relevant memories."""
        collection = self.collections[collection_name]

        if collection.count() == 0:
            return []

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

            if relevance < config.RETRIEVAL_MIN_RELEVANCE:
                continue

            doc_id = results["ids"][0][i]
            meta = results["metadatas"][0][i] if results["metadatas"] else {}

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

    def count(self, collection_name: str) -> int:
        return self.collections[collection_name].count()

    def get_stats(self) -> dict:
        return {name: col.count() for name, col in self.collections.items()}
