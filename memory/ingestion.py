"""
Markdown document ingestion.

Watches ./memory/docs/ for .md files, chunks them by heading or fixed size,
and stores them in the ChromaDB documents collection.
"""

import os
import hashlib
import re
import config
from memory.vector_store import VectorStore


def chunk_by_heading(text: str, source: str) -> list[dict]:
    """Split markdown by headings, falling back to fixed-size chunks."""
    chunks = []

    # Split on markdown headings (## or ###)
    sections = re.split(r'\n(?=#{1,3} )', text)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # If a section is too large, split it further
        if len(section) > config.CHUNK_SIZE:
            sub_chunks = chunk_fixed_size(section, source)
            chunks.extend(sub_chunks)
        else:
            # Extract heading if present
            heading_match = re.match(r'^(#{1,3})\s+(.+)', section)
            heading = heading_match.group(2) if heading_match else ""

            chunks.append({
                "text": section,
                "heading": heading,
                "source": source,
            })

    # If no headings found, fall back to fixed-size chunking
    if len(chunks) <= 1 and len(text) > config.CHUNK_SIZE:
        return chunk_fixed_size(text, source)

    return chunks


def chunk_fixed_size(text: str, source: str) -> list[dict]:
    """Split text into fixed-size chunks with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + config.CHUNK_SIZE

        # Try to break at a paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind('\n\n', start, end)
            if para_break > start + config.CHUNK_SIZE // 2:
                end = para_break
            else:
                # Look for sentence break
                sentence_break = text.rfind('. ', start, end)
                if sentence_break > start + config.CHUNK_SIZE // 2:
                    end = sentence_break + 1

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "heading": "",
                "source": source,
            })

        start = end - config.CHUNK_OVERLAP if end < len(text) else len(text)

    return chunks


def file_hash(filepath: str) -> str:
    """Get a hash of file contents for change detection."""
    with open(filepath, "r") as f:
        return hashlib.md5(f.read().encode()).hexdigest()


def ingest_documents(vector_store: VectorStore, docs_dir: str | None = None) -> int:
    """
    Scan docs_dir for .md files and ingest any new or changed ones.
    Returns the number of new chunks added.
    """
    docs_dir = docs_dir or config.DOCS_DIR
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir, exist_ok=True)
        return 0

    total_added = 0

    for filename in os.listdir(docs_dir):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(docs_dir, filename)
        current_hash = file_hash(filepath)

        # Check if this file (with this hash) is already ingested
        existing = vector_store.collections["documents"].get(
            where={"$and": [{"source_file": filename}, {"file_hash": current_hash}]}
        )
        if existing["ids"]:
            continue  # Already ingested this version

        # Remove old version of this file if it exists
        vector_store.delete_by_metadata("documents", {"source_file": filename})

        # Read and chunk the file
        with open(filepath, "r") as f:
            content = f.read()

        chunks = chunk_by_heading(content, filename)
        if not chunks:
            continue

        # Store chunks
        texts = [c["text"] for c in chunks]
        metadatas = [
            {
                "source_file": filename,
                "file_hash": current_hash,
                "heading": c["heading"],
                "chunk_index": i,
            }
            for i, c in enumerate(chunks)
        ]
        ids = [f"doc_{filename}_{i}" for i in range(len(chunks))]

        vector_store.add_batch("documents", texts, metadatas, ids)
        total_added += len(chunks)

        if config.LOG_TOKEN_USAGE:
            print(f"  [ingest] {filename}: {len(chunks)} chunks ingested")

    return total_added
