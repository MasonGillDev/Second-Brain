# Memory Extraction Cost Optimization (TODO)

**Date:** 2026-04-07
**Status:** Not yet implemented — revisit when token costs become noticeable

---

## Problem

The `extract_memories()` method in `manager.py` has two scaling issues:

### 1. Dedup Query Uses Full Conversation Text
Currently the dedup lookup passes the entire recent conversation as the query string to ChromaDB:
```python
existing_memories = self.vector_store.query("long_term", msg_text, top_k=10)
```
This is wasteful — we only need to check if the *facts being extracted* already exist, not match against the full conversation blob.

### 2. Extraction Prompt Grows with Memory Count
The prompt includes existing memories to avoid duplicates:
```
## Existing Memories (do not duplicate these)
{existing_memories}
```
As `long_term` fills up (100+ entries), this section balloons the prompt size, increasing Haiku token cost every 5 exchanges.

---

## Proposed Fixes

### Fix 1: Use Only User Messages for Dedup Query
Filter to just user messages instead of the full conversation (user + assistant). User messages contain the actual facts; assistant responses are mostly filler for dedup purposes.

### Fix 2: Cap Dedup Memories
Reduce `top_k` from 10 to 5 for the dedup query. 5 relevant existing memories is enough context for Haiku to avoid duplicates.

### Fix 3: Budget the Extraction Prompt
Add a max token limit for the `existing_memories` section in the extraction prompt. If existing memories exceed the budget, truncate to the most relevant ones.

### Fix 4: Two-Pass Extraction (Advanced)
1. First, extract candidate memories (no dedup check — cheap, short prompt)
2. Then, for each candidate, do a targeted ChromaDB similarity search to check if it already exists
3. Only store if no close match found

This avoids stuffing all existing memories into the prompt entirely. The ChromaDB query is free (local), and we skip the LLM dedup altogether.

---

## Cost Estimation

At current usage (~5 exchanges per extraction):
- Haiku input: ~500-1000 tokens per extraction call
- With 100 stored memories in dedup section: ~2000-3000 tokens per call
- Fix 4 would bring it back down to ~500 tokens regardless of memory count
