# Memory System Full Audit

**Date:** 2026-04-20
**Status:** Active

---

## Overview

Complete audit of the Second Brain memory system — its architecture, data flow, configuration, and improvement opportunities. This system provides persistent, multi-tiered memory for a Claude-powered AI agent accessible via Telegram, scheduled tasks, and a dashboard.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER MESSAGE (Telegram / Scheduler)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  WORKING MEMORY (conversation.py)                               │
│  • Stores raw messages in a buffer                              │
│  • Rolling summary replaces old messages when buffer > 20       │
│  • Always keeps last 5 messages verbatim                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CONTEXT ASSEMBLY (manager.py → build_messages)                 │
│                                                                  │
│  System Prompt:                                                  │
│    • Personality (from personality.txt)                          │
│    • Memory type descriptions                                   │
│    • Skill manifest (available tools)                            │
│    • Retrieved memories (from vector store)                     │
│                                                                  │
│  Messages:                                                       │
│    • Rolling summary (injected as user+assistant pair)           │
│    • Last 5 recent messages                                     │
│    • Current user query                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LLM CALL (Claude Sonnet 4) + TOOL LOOP (max 7 rounds)         │
│  • Agent can call store_memory, search_memory, etc.             │
│  • Agent can activate skills (filesystem, calendar, etc.)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST-RESPONSE: AUTO-EXTRACTION (every 7 exchanges)             │
│  • Haiku reviews recent conversation                            │
│  • Extracts facts passing the "2-week test"                     │
│  • Each fact → dedup_and_store() → SKIP / MERGE / STORE        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PERIODIC CONSOLIDATION (every 100 exchanges)                   │
│  • Clusters similar memories (similarity > 0.7)                 │
│  • Merges clusters via Haiku                                    │
│  • Deletes originals, stores merged version                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Memory Tiers (Vector Store Collections)

| Collection | Purpose | How Data Gets In | Retrieval top_k |
|---|---|---|---|
| `long_term` | Facts, preferences, decisions | Auto-extraction + agent `store_memory` tool | 3 |
| `episodic` | Interaction summaries with outcomes | `store_episode()` (manual/code) | 2 |
| `procedural` | How-to knowledge, step-by-step | `store_procedure()` (manual/code) | 2 |
| `reference` | Useful but not daily info | Agent storage, sleep agent moves | 3 |
| `documents` | Ingested .md/.docx files | Auto-ingested from `./memory/docs/` | 3 |
| `archive` | Outdated/retired memories | Sleep agent moves here | — (not queried) |

---

## The Conversation Layer (`memory/conversation.py`)

### Working Memory
- Buffer of raw messages (role + content)
- **Threshold**: When buffer exceeds `WORKING_MEMORY_MIN_MESSAGES + SUMMARIZE_EVERY_N_MESSAGES` (5 + 15 = 20), summarization triggers

### Rolling Summary
- Structured markdown produced by Haiku with sections:
  - Current Goals
  - Key Facts Established
  - Decisions Made
  - Open Questions
  - Context
- Replaces old messages — only the last 5 are kept verbatim
- Injected into API call as a user message + assistant acknowledgment pair

### Session Persistence
- Saved to `./memory/data/session.json` after every exchange
- Contains: messages array, rolling_summary string, total_messages_processed count
- Scheduler uses a separate file: `./memory/data/session_scheduler.json`

---

## Retrieval Flow (`manager.py → retrieve_context`)

### Skip Logic (saves tokens)
1. Message has fewer than `RETRIEVAL_MIN_WORDS` (2) words → skip
2. Message matches `RETRIEVAL_SKIP_PATTERNS` (yes, no, ok, thanks, etc.) → skip

### Query Process
1. Query each collection with its configured top_k
2. Filter results below `RETRIEVAL_MIN_RELEVANCE` (0.3 general, 0.39 for reference)
3. Update access metadata (last_accessed, access_count) on every hit
4. Format results into a "Retrieved Memories" section
5. Trim if total exceeds `BUDGET_RETRIEVED_MEMORIES` allocation (2400 tokens)

### Relevance Scoring
- ChromaDB returns L2 distance
- Converted to relevance: `1 / (1 + distance)`
- Range: 0 to 1 (higher = more relevant)

---

## Memory Extraction (`manager.py → extract_memories`)

- **Trigger**: Every 7 exchanges (configurable via `EXTRACT_EVERY_N_EXCHANGES`)
- **Model**: Haiku (cheap)
- **Prompt logic**: "What facts from this conversation would be useful to recall 2 weeks from now?"
- **Extracts**: Identity facts, preferences, decisions, project context, relationships
- **Filters OUT**: Casual conversation, questions asked, tone/personality, things already in context
- **Output**: JSON array of `{text, category}` pairs
- **Each fact** → `dedup_and_store()` before insertion

---

## Deduplication (`memory/maintenance.py → dedup_and_store`)

Runs on every write to long_term memory:

1. Query top 3 most similar existing memories
2. Filter to those above similarity 0.5
3. If no similar memories → **STORE** directly
4. If similar exist → Ask Haiku to decide:
   - **SKIP**: Already known (don't store)
   - **STORE**: Genuinely new information
   - **MERGE**: Combine with existing, delete old, store merged

---

## Consolidation (`memory/maintenance.py → consolidate`)

- **Trigger**: Every 100 exchanges OR on shutdown (if enabled)
- **Process**:
  1. Get all long_term memories (capped at 100)
  2. Find similarity clusters (threshold: 0.7)
  3. Max cluster size: 2 (prevents over-merging)
  4. For each cluster: Haiku merges → delete originals → store merged
- **Currently disabled on shutdown** (`CONSOLIDATE_ON_SHUTDOWN = False`)

---

## Document Ingestion (`memory/ingestion.py`)

- **Watch directory**: `./memory/docs/`
- **Formats**: `.md`, `.docx`
- **Change detection**: MD5 hash per file — only re-ingests on change
- **Chunking strategy**:
  - Primary: Split by markdown headings (## or ###)
  - Fallback: Fixed-size chunks (1000 chars, 200 overlap)
  - Boundary-aware: prefers paragraph/sentence breaks
- **Storage**: `documents` collection with metadata (source_file, file_hash, heading, chunk_index)
- **Runs**: On startup (`_ingest_docs_on_start()`) and on-demand via `ingest_docs()`

---

## Sleep Agent (`memory/sleep_tools.py` + `memory/recursive_search.py`)

An autonomous agent designed for offline memory maintenance.

### Recursive Similarity Search
- Seeds: Memories from last 24 hours
- BFS expansion: up to 3 hops deep, 5 results per hop
- Relevance decays per hop: `relevance *= 0.85`
- Hard caps: 35 memories, 5 document chunks

### Available Tools
| Tool | Purpose |
|---|---|
| `search_memories` | Semantic search by tier |
| `update_memory` | Rewrite memory text |
| `split_memory` | Break one memory into multiple |
| `merge_memories` | Combine related memories |
| `move_memory` | Relocate between tiers |
| `tag_memory` | Update category metadata |

### Loop Constraints
- Max 15 tool rounds per run
- Max 20 total LLM calls
- Logs to `./memory/data/sleep_logs/`

---

## MCP Memory Server (`mcp_servers/memory_server.py`)

Tools exposed to the agent during conversation:

| Tool | Description |
|---|---|
| `store_memory(text, category)` | Store a fact with dedup |
| `search_memory(query, top_k)` | Semantic search long_term |
| `list_all_memories()` | Dump all (up to 50) |
| `delete_memory(memory_id)` | Remove by ID |
| `get_personality()` | Read personality.txt |
| `update_personality(personality)` | Write personality.txt (max 500 chars) |

---

## Configuration Reference (`config.py`)

### Model Settings
| Variable | Value | Purpose |
|---|---|---|
| `MODEL` | `claude-sonnet-4-20250514` | Main conversation model |
| `SUMMARIZATION_MODEL` | `claude-haiku-4-5-20251001` | Cheap model for summarization, extraction, dedup, consolidation |
| `MAX_RESPONSE_TOKENS` | 1024 | Max output per response |

### Context Budget (16,000 tokens total)
| Variable | Value | Tokens | Purpose |
|---|---|---|---|
| `BUDGET_SYSTEM_PROMPT` | 0.15 | ~2,400 | System prompt + personality + skill manifest |
| `BUDGET_SUMMARY` | 0.20 | ~3,200 | Rolling conversation summary |
| `BUDGET_RETRIEVED_MEMORIES` | 0.15 | ~2,400 | Vector DB retrievals |
| `BUDGET_WORKING_MEMORY` | 0.50 | ~8,000 | Recent messages (live conversation) |

### Conversation
| Variable | Value | Purpose |
|---|---|---|
| `WORKING_MEMORY_MIN_MESSAGES` | 5 | Always keep this many recent messages unsummarized |
| `SUMMARIZE_EVERY_N_MESSAGES` | 15 | Buffer threshold before triggering summarization |
| `MAX_SUMMARY_TOKENS` | 3200 | Max rolling summary size |

### Retrieval
| Variable | Value | Purpose |
|---|---|---|
| `RETRIEVAL_TOP_K_LONG_TERM` | 3 | Results from long_term per query |
| `RETRIEVAL_TOP_K_EPISODIC` | 2 | Results from episodic per query |
| `RETRIEVAL_TOP_K_PROCEDURAL` | 2 | Results from procedural per query |
| `RETRIEVAL_TOP_K_REFERENCE` | 3 | Results from reference per query |
| `RETRIEVAL_TOP_K_DOCUMENTS` | 3 | Results from documents per query |
| `RETRIEVAL_MIN_RELEVANCE` | 0.3 | Floor for inclusion (general) |
| `RETRIEVAL_MIN_RELEVANCE_REFERENCE` | 0.39 | Floor for reference tier (stricter) |
| `RETRIEVAL_MIN_WORDS` | 2 | Skip retrieval for messages shorter than this |
| `RETRIEVAL_SKIP_PATTERNS` | [list] | Exact phrases that bypass retrieval |

### Document Ingestion
| Variable | Value | Purpose |
|---|---|---|
| `DOCS_DIR` | `./memory/docs` | Watch directory for documents |
| `CHUNK_SIZE` | 1000 | Characters per chunk |
| `CHUNK_OVERLAP` | 200 | Overlap between chunks |

### Memory Extraction
| Variable | Value | Purpose |
|---|---|---|
| `AUTO_EXTRACT_MEMORIES` | True | Enable auto-extraction |
| `EXTRACT_EVERY_N_EXCHANGES` | 7 | How often to run extraction |
| `IMPORTANCE_THRESHOLD` | 0.5 | Minimum importance score for storage |

### Deduplication
| Variable | Value | Purpose |
|---|---|---|
| `DEDUP_TOP_K` | 3 | Compare against this many similar memories |
| `DEDUP_MIN_RELEVANCE` | 0.5 | Similarity floor to consider as duplicate |

### Consolidation
| Variable | Value | Purpose |
|---|---|---|
| `CONSOLIDATE_EVERY_N_EXCHANGES` | 100 | How often to run batch consolidation |
| `CONSOLIDATE_ON_SHUTDOWN` | False | Whether to consolidate when agent shuts down |
| `CONSOLIDATION_BATCH_LIMIT` | 100 | Max memories processed per consolidation run |
| `CONSOLIDATION_SIMILARITY_THRESHOLD` | 0.7 | Similarity needed to cluster memories |
| `CONSOLIDATION_MAX_CLUSTER_SIZE` | 2 | Max memories per merge cluster |

### Sleep Agent
| Variable | Value | Purpose |
|---|---|---|
| `SLEEP_AGENT_ENABLED` | True | Master toggle |
| `SLEEP_MODEL` | Haiku | Model used for sleep operations |
| `SLEEP_SEARCH_DEPTH` | 3 | Max BFS hops from seed memories |
| `SLEEP_SIMILARITY_DECAY` | 0.85 | Relevance decay per hop |
| `SLEEP_TOP_K_PER_HOP` | 5 | Results per search at each depth |
| `SLEEP_MIN_RELEVANCE` | 0.25 | Floor after decay |
| `SLEEP_MAX_CONTEXT_MEMORIES` | 35 | Hard cap on memories per run |
| `SLEEP_MAX_DOCUMENT_MEMORIES` | 5 | Hard cap on document chunks |
| `SLEEP_MIN_DOCUMENT_RELEVANCE` | 0.45 | Documents must be highly relevant |
| `SLEEP_SEED_LOOKBACK_HOURS` | 24 | "Recent" = last N hours |
| `SLEEP_MAX_SEEDS` | 15 | Max seed memories to start from |
| `SLEEP_MAX_TOOL_ROUNDS` | 15 | Max tool loop iterations |
| `SLEEP_MAX_LLM_CALLS` | 20 | Hard cap on API calls |

### Cost & Persistence
| Variable | Value | Purpose |
|---|---|---|
| `INPUT_COST_PER_1K` | 0.003 | Sonnet input rate (logging only) |
| `OUTPUT_COST_PER_1K` | 0.015 | Sonnet output rate (logging only) |
| `TOKEN_ESTIMATION_MULTIPLIER` | 1.3 | words × this ≈ tokens |
| `LOG_TOKEN_USAGE` | True | Console logging of token spend |
| `SESSION_FILE` | `./memory/data/session.json` | Conversation persistence |
| `PERSONALITY_FILE` | `./memory/data/personality.txt` | Agent persona |
| `PERSONALITY_MAX_CHARS` | 500 | Personality length cap |

### Runtime Overrides
- File: `./memory/data/config_overrides.json`
- Any uppercase key in that JSON overrides the matching config variable
- Reloaded before every message via `config.reload_overrides()`
- Used by the dashboard for live tuning without restart

---

## Multi-Interface Support

| Interface | Session File | Long-Term DB | Notes |
|---|---|---|---|
| Telegram Bot | `session.json` | Shared ChromaDB | Primary interface |
| Scheduler | `session_scheduler.json` | Shared ChromaDB | Injects results back to Telegram session |
| Dashboard | — | Reads ChromaDB | Config editor writes `config_overrides.json` |

---

## Improvement Opportunities

### High Priority

- [ ] **Episodic memory is underutilized** — `store_episode()` exists but nothing in the main flow calls it automatically. Consider auto-generating episodes at session boundaries or after significant tool interactions.

- [ ] **No TTL / decay mechanism** — Memories accumulate forever. Old, never-accessed memories should be auto-archived or deleted. The access_count metadata exists but nothing acts on it.

- [ ] **Consolidation max cluster size of 2 is very conservative** — Raising to 3-4 would allow more aggressive merging for memory hygiene. Current setting means deeply related clusters of 3+ memories stay fragmented.

- [ ] **Extraction prompt doesn't see tool results** — If the agent runs tools (filesystem reads, calendar lookups), those results contain facts that should be extractable but may not make it into the extraction window.

- [ ] **No embedding model versioning** — If ChromaDB's default embedding model changes between versions, old vectors become incompatible with new queries. Should pin or track embedding model version.

### Medium Priority

- [ ] **Sleep agent not integrated into main loop** — `SLEEP_AGENT_ENABLED = True` but there's no trigger that actually runs it. Needs a scheduler entry or shutdown hook to invoke it periodically.

- [ ] **No memory importance scoring at retrieval time** — All memories above the relevance threshold are treated equally. Could weight by access_count, recency, or importance score.

- [ ] **Budget is very tight at 16K total** — With 2400 tokens for retrieval across 5 collections, each memory gets ~160 tokens max. Consider raising to 24K or 32K for richer context (cost increase is modest with Sonnet).

- [ ] **Rolling summary is lossy** — Once summarized, original messages are gone. If the summary misses something, that information is lost. Consider keeping a full session log on disk (not sent to API, but available for re-extraction).

- [ ] **No cross-session continuity signal** — When a new session starts, there's no "last time we talked about X" warm-up. The rolling summary is gone after clear. Episodic memories could fill this gap if auto-generated.

- [ ] **Document ingestion doesn't handle PDFs** — Only .md and .docx. PDF support (via PyPDF2 or pdfplumber) would expand the knowledge base significantly.

### Low Priority / Nice-to-Have

- [ ] **No memory search exposed to user** — User can `/memories` to list all, but can't do a semantic search from Telegram. A `/search <query>` command would be useful.

- [ ] **Dedup LLM calls are synchronous** — Each extracted fact makes a separate Haiku call for dedup. Could batch these into one call with multiple comparison sets.

- [ ] **No confidence/source tracking** — Memories don't track whether they came from auto-extraction, user explicit storage, or document ingestion. This would help the agent weight trust levels.

- [ ] **Procedural memories have no trigger mechanism** — They're stored but only retrieved by semantic similarity. A pattern-matching trigger ("when the user asks to deploy...") would make them more actionable.

- [ ] **Config overrides don't validate** — Any uppercase key gets accepted. A typo like `RETIREVAL_MIN_RELEVANCE` would silently create a new variable instead of overriding the intended one.

- [ ] **No memory export/backup** — ChromaDB data lives in `./memory/data/chroma/`. Should have a periodic backup or export-to-JSON mechanism.

- [ ] **Token estimation is approximate** — `words * 1.3` is a rough heuristic. Using `tiktoken` or Anthropic's tokenizer would give exact counts for budget management.

---

## Cost Profile (Estimated)

| Operation | Model | Frequency | Est. Cost/Message |
|---|---|---|---|
| Main conversation | Sonnet | Every message | ~$0.06-0.10 |
| Summarization | Haiku | Every ~15 messages | ~$0.002 |
| Memory extraction | Haiku | Every 7 exchanges | ~$0.003 |
| Dedup check | Haiku | Per extracted fact | ~$0.001 |
| Consolidation | Haiku | Every 100 exchanges | ~$0.01 |

**Key cost lever**: `TOTAL_CONTEXT_BUDGET` directly controls input cost. At 16K tokens, input cost per Sonnet call is ~$0.048. The Haiku maintenance operations are negligible by comparison.

---

## File Index

| File | Role |
|---|---|
| `config.py` | All tunable parameters |
| `core.py` | Main agent loop, orchestrates memory flow |
| `memory/manager.py` | Central memory orchestrator |
| `memory/conversation.py` | Working memory + rolling summary |
| `memory/vector_store.py` | ChromaDB wrapper (6 collections) |
| `memory/ingestion.py` | Document chunking and loading |
| `memory/maintenance.py` | Dedup + consolidation |
| `memory/recursive_search.py` | Sleep agent BFS search |
| `memory/sleep_tools.py` | Sleep agent tool definitions |
| `mcp_servers/memory_server.py` | MCP tools (store, search, delete, personality) |
| `telegram_bot.py` | Telegram interface + memory commands |
| `scheduler.py` | Scheduled tasks with separate session |
| `dashboard_server.py` | Web dashboard + config editor |
