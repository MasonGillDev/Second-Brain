# Boomy V1 — Build Plan (Memory-First Companion)

**Project:** Boomy
**Date:** 2026-08-25
**Author:** adf79393-82a8-4ae0-a659-199f0c21574e
**Directory:** /Users/masongill/Boomy

## What Was Done

### M3 complete — capture pipeline (2026-08-26)

Attachment ingestion end to end: storage, extractors, chunking, Claude vision, and the
`/chat/attach` endpoint. 100 tests green, ruff clean, migrations round-trip, retrieval
eval back at 1.00.

- **`app/infra/storage.py`** — `Storage` protocol + local filesystem (S3 later). Blobs
  are content-addressed per user, so re-sending the same screenshot reuses one file
  instead of paying a fresh extraction and a fresh set of embeddings.
- **`app/ingest/extractors.py`** — PDF (pypdf), DOCX (incl. table cells, where invoices
  and schedules keep the actual content), text, images. HEIC flagged for conversion —
  it is the iPhone default, so that is the main path, not an edge case.
- **`app/ingest/chunking.py`** — ~500-token overlapping chunks, splitting on paragraphs
  then sentences, cutting mid-sentence only for text with no structure at all.
- **`app/ingest/describe.py`** — one Claude call per attachment yields description *and*
  any text in it, which is why §8.2's OCR line item needed no separate service. Scanned
  PDFs go to the model as native document blocks.
- **`app/ingest/pipeline.py`** — parent artifact + chunk records, one embedding request
  for the whole document via `write_many()`.

**Verified live, twice.** A 3-page PDF: described accurately, then the agent searched,
created `work/new-hires`, **moved the artifact out of `inbox`**, and wrote four facts —
and all three recall queries answered from it in a fresh session. Then a longer document
specifically to exercise chunking (the first PDF fitted in one chunk, so that path had
not actually run): 2 chunks, bucket count still 1, and *"how long before I can take
extended leave"* — sharing almost no wording with "twelve-week paid sabbatical" — matched
through chunk embeddings and folded back up to the document.

**The keyword half was wrong and a test caught it by accident.** `websearch_to_tsquery`
ANDs its terms, so a fuzzy query mostly made of words the record never used matched
nothing. I switched to OR — and the eval said recall@1 dropped 1.00 → 0.92. Diagnosing
per-query showed why: `ts_rank_cd` has no IDF, so "do I need to sort my passport" matched
"The pharmacy **needs** 48 hours notice" on the stem `need` and outranked the passport
record. The fix is neither: AND by default, OR **only when the whole search returned
nothing**. When AND matches nothing that is usually information, and the vector half
alone beats the vector half plus loose noise. Back to 1.00.

Worth noting as method: my reasoning about OR was plausible and wrong, and only the
measurement caught it. The eval paid for itself here.

### M2 complete — agent runtime (2026-08-25)

The 8 memory tools, the tool-runner loop, session boundaries with episode writing, and
chat endpoints. 73 tests green, ruff clean, retrieval eval still passing.

- **`app/agent/tools.py`** — the eight tools (§5.4), built per-request bound to one
  user's store. They take no `user_id` argument on purpose: that would put a tenancy
  boundary somewhere the model can reach. Tool *descriptions* carry the filing policy,
  since that's where the reuse-vs-create decision is actually made.
- **`app/agent/prompts.py`** — persona split from per-session context for caching.
- **`app/agent/sessions.py`** — idle (30min) and background (10min) boundaries; a new
  session starts with an empty message list, which is what makes §5.5's "never load full
  history" structural rather than aspirational. Episode written on close.
- **`app/agent/runtime.py`** — tool-runner loop with the cache layout
  `tools → PERSONA ⟨breakpoint⟩ → session context → messages`.
- **`app/api/chat.py`** — send / thread / backgrounded.

**Verified live (2026-08-26).** Three capture turns, a forced session boundary, then
three recall queries. Behaviour was good on every axis that matters:

- **No bucket sprawl** — 3 buckets for 3 distinct subjects; searched before filing every
  single time; nothing near-duplicated.
- **Facts split atomically and written self-contained** — "Onboarding for the new
  platform team engineers must be complete by September 12 (per a call with Dana, the
  platform team hiring manager)", not "it's due Sept 12".
- **Recall across a session boundary worked from memory alone** — first recall turn had
  `started_new_session=True` and an empty transcript, and still answered correctly.
- **It admitted ignorance.** Asked for a dentist it had never been told about, it said
  so and named the nearest thing it held, rather than inventing one. That is §4.2 and
  the distance floor doing their job on a real query.
- **Tone matched** — lowercase, casual input got short lowercase-register replies.

**Prompt caching confirmed with real usage**, not just the layout test: 2,972 tokens
read from cache on every one of the 12 requests, with only 148–1,400 uncached (the
volatile session context plus the growing turn). The stable persona+tools prefix is
never re-billed at full rate.

One wobble worth knowing: bucket *naming* is non-deterministic across fresh users — the
same input produced `home/renovation` on one run and `home/kitchen-remodel` on the next.
Harmless in practice, since within a single user the first name sticks and search makes
later items reuse it, but don't expect stable names across accounts.

Six bugs found by building it, five of which would have hit production:

1. **A rejected write poisoned the whole turn.** A CHECK violation aborts the Postgres
   transaction, so the agent's *next* write in the same turn failed for reasons it could
   neither see nor recover from. Tool mutations now run in savepoints.
2. **A hallucinated record id crashed the turn** — `_parse_uuid` raised where the tools
   only caught `RecordNotFound`. Models hallucinate ids; every tool path now returns text.
3. **Thread ordering was undefined.** `created_at`'s server default is `now()`, which in
   Postgres is *transaction* time — every message written in one transaction shared a
   timestamp, so the user would see their own turns shuffled. Added a monotonic `seq`.
4. **Alembic silently wrote no migration file.** The `func.to_tsvector("english", ...)`
   index compiles the config name to a bindparam that autogenerate can't render; it
   raised CompileError mid-write and left nothing behind, looking exactly like alembic
   doing nothing. Expressed as literal SQL instead.
5. **Every new user's first session close crashed.** The episode writes to `profile`,
   but nothing creates that bucket — the agent only makes buckets for subjects the user
   raises. Found by the first live run, not by any unit test. `profile` is infrastructure
   rather than a topic, so it is now created on demand, and the whole episode step is
   best-effort so nothing there can block a session closing.
6. **Autogenerate proposed dropping both search indexes**, because raw-SQL indexes are
   invisible to model metadata. Declaring them in `__table_args__` fixed it — otherwise
   someone eventually applies that migration and hybrid search quietly disappears.
   (The enum-drop trap from M0 recurred for `message_role`; alembic does this for every
   new enum.)

### M1 complete — memory layer, measured (2026-08-25)

Embeddings vendor decided: **Voyage `voyage-3.5`**, 1024-dim. Running local-only for a
while, so auth and object storage stay deferred. 36 tests green, ruff clean.

**Eval result — 1.00 recall@1, MRR 1.00, hard@3 7/7** (13 queries, 12 records, ~7s).
The vector-only queries all landing at rank 1 confirms the wiring: asymmetric
`input_type`, matching dimensions, cosine distance, and a floor that isn't over-filtering.
**Read it as a smoke test passing, not as evidence retrieval is good** — 12 records
across 6 well-separated topics is an easy problem, and any competent model separates
"dentist" from "deploy freeze". The corpus needs scale, near-duplicates, and deliberate
distractors (two facts about one project; three dentist appointments where one is
current) before the thresholds discriminate anything. Growing it is the highest-value
follow-up in M1.

- **`app/infra/embeddings.py`** — `Embedder` protocol with `VoyageEmbedder` and a
  deterministic `FakeEmbedder`. Two methods (`embed_documents` / `embed_query`) rather
  than one because Voyage embeds asymmetrically via `input_type`, and using the wrong
  side costs recall silently. `build_embedder()` warns loudly when it falls back.
- **`app/memory/search.py`** — dense KNN + Postgres FTS fused with RRF, then boosted by
  recency (30-day half-life) and access count (log-bounded). RRF rather than a weighted
  score sum because cosine distance and `ts_rank_cd` aren't comparably scaled and
  `ts_rank_cd` isn't normalized at all, so any fixed weighting drifts with corpus size.
- **Chunk folding** — chunk hits resolve up to their parent artifact with sqrt-damped
  score accumulation, so a long document can't win on chunk count alone. `matched_via`
  records which chunks fired.
- **`app/agent/context.py`** — session-start context under a 1000-token budget, with an
  ordered trim (episodes → open items → facts). The bucket index is never trimmed:
  without it, filing degenerates into a new bucket per message, which is §11's sprawl.
- **`evals/`** — 13-query corpus, 7 of them vector-only, reporting recall@1/3/5 + MRR
  and failing below threshold. Refuses to run on `FakeEmbedder`.

Four things found by building it:

1. **Vector KNN has no relevance floor** — it returns its nearest N however unrelated,
   so an absurd query came back looking confident. Added `max_cosine_distance` (0.75).
   This isn't just hygiene: §4.2 requires the agent to say when confidence is low, and
   without a floor there was no signal to say it *from*. Wants tuning against real
   Voyage vectors.
2. **`revise()` was dropping the embedding.** The new record copied every field except
   the vector, so every revised fact silently fell out of vector search while still
   looking healthy in the browser. Now re-embeds — the content changed, so the old
   vector was wrong anyway. Regression test added.
3. **One embedding call per record made seeding take ~5 minutes.** Voyage's free tier
   allows 3 requests/minute, and `write()` embeds a single record per call — so the
   12-record eval corpus burned 12 requests. Added `store.write_many()`, which embeds
   the batch in one request; the eval went from ~5 min to 6.7s. This matters well beyond
   the eval: in M3 a PDF becomes ~50 chunks, which would have been ~17 minutes and 50
   requests per document. `VoyageEmbedder` also now retries rate limits with backoff.
4. **Two eval queries were mislabelled `hard`**, sharing vocabulary with their targets;
   a corpus-hygiene test caught it. They'd have been passed by keyword search while
   appearing to prove the vector half worked. Reclassified, not rewritten — one is
   verbatim from §4.2, and real queries are rarely pure.

### M0 complete — schema + store (2026-08-25)

Scaffolded `backend/` and shipped the foundation milestone. Verified: 10 store tests
pass, `alembic downgrade base && upgrade head` cycles cleanly twice, `/health` returns
`{"status":"ok","db":"ok"}` against a live DB, `ruff check` clean.

- **Postgres 16 + pgvector via docker-compose on port 5433** (5432 left free for any
  local install). Volume `boomy-pgdata`.
- **`app/memory/models.py`** — `users`, `buckets`, `memory_records` per §5.2/§5.3, with
  the two departures from the doc's schema noted in §4 below (`superseded_by`,
  `parent_id`). Enums are native PG types via `StrEnum` + `values_callable`.
- **`app/memory/store.py`** — `MemoryStore`, the sole mutator of memory. Implements
  write / read / revise / move / list_bucket / active_facts / bucket CRUD. `search()`
  is M1.
- **Indexes**: HNSW `vector_cosine_ops` on `embedding`, GIN on
  `to_tsvector('english', content)` — both halves of §5.5 hybrid search ready before
  M1 needs them. Partial index on the current-belief predicate.
- **Two invariants enforced in the database, not just in code**: a CHECK constraint
  makes `source='inferred' AND confidence >= 0.8` unrepresentable (§5.2), and the
  current-belief predicate is a partial index rather than an anti-join.

Three things worth knowing:

1. **`revise()` never edits content in place.** It writes a new row, retires the old
   one, and links both directions. `move()` deliberately does *not* supersede — refiling
   isn't a belief change. Both are covered by tests.
2. **Chunks don't inflate `item_count`** and don't surface in `list_bucket()`; the
   browser shows artifacts, and chunks hide behind their parent (§4.3, §6.2).
3. **Bug found and fixed during verification**: alembic's autogenerated downgrade drops
   tables but leaves the PG enum types behind, so `downgrade base` then `upgrade head`
   failed on "type bucket_type already exists". The downgrade now drops the five enum
   types explicitly.

Setup and run instructions are in `/Users/masongill/Boomy/README.md`. Repo is
`git init`-ed with the M0 tree staged but not committed.

---

## Original plan

Took the V1 scope doc (memory-first AI companion, iOS + cloud backend) and turned it
into a concrete implementation plan. `/Users/masongill/Boomy` was empty — this is
greenfield. No code written yet; this doc is the plan and the decision record.

**Scoped as a demo first pass** (decision, 2026-08-25): the §4.1 3-second acknowledgment
target and the §8.3 encryption-at-rest requirement are both **out** for this pass. See
§6 for what that removes.

---

## 1. Tech stack decisions

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.12 + FastAPI** (async, uvicorn) | Document extraction ecosystem (pypdf, python-docx, unstructured) is materially better than Node's. Anthropic Python SDK has the most mature tool-runner + memory helpers. Trade-off: one more language than an all-TS shop would want. |
| DB | **Postgres 16 + pgvector** | Per spec. HNSW index on `embedding`, GIN + `tsvector` for keyword half of hybrid search. |
| Object storage | **S3 (or R2)** | Artifact binaries, presigned URLs for client fetch. |
| Queue | **Postgres-backed job queue** (SkipLocked) or Redis+arq | Document ingestion and nightly consolidation. Don't add Redis until needed. |
| Client | **SwiftUI, iOS 17+** | Per spec. SQLite via GRDB for local cache + outbound queue. |
| Agent | **Anthropic API + tool runner** (`client.beta.messages.tool_runner`) | Not Managed Agents — we own the memory store and want the tool loop in our process, next to Postgres. CMA's hosted sandbox buys us nothing here. |

### Model choice

Default **`claude-opus-5`** everywhere. Retrieval quality is the product (§10: "if recall
quality is mediocre, nothing else matters"), so don't start by optimizing cost.

| Job | Model | Config |
|---|---|---|
| Chat / filing pass | `claude-opus-5` | `effort: "medium"`, streaming. (No fast mode — the latency target is dropped, so spend the budget on filing quality instead.) |
| Retrieval answer | `claude-opus-5` | `effort: "medium"`, streaming |
| Vision / OCR | `claude-opus-5` | Native vision, 2576px long edge, ~4784 tok/image |
| Nightly consolidation | `claude-opus-5` | `effort: "high"`, batch API (50% off, latency irrelevant) |

Notes that matter:
- Opus 5 pricing is $5/$25 per MTok. Fast mode ($10/$50, Claude-API-only) exists if the
  latency target ever comes back — it is not needed for the demo.
- Thinking is **on by default** on Opus 5 — `max_tokens` caps thinking + text together. Size accordingly.
- Do **not** set `thinking: {type:"disabled"}` to save latency: on Opus 5 that has two
  failure modes (tool calls emitted as plain text that silently never run; `<thinking>`
  tags leaking into output). Use `effort: "low"` instead.
- Prompt-cache minimum on Opus 5 is 512 tokens — our system prompt + tool defs will cache.
- Sonnet 5 / Haiku 4.5 are cost levers to pull **after** measuring, not before.

### Non-Anthropic dependencies (the spec doesn't name these — they're required)

1. **Embeddings.** Anthropic has no embeddings endpoint. Recommend **Voyage AI
   (`voyage-3.5`)**, 1024-dim. Wrap behind an `Embedder` protocol so the model is
   swappable — but note re-embedding the whole corpus on a swap is a real migration.
2. **Transcription.** Recommend **on-device iOS Speech framework** for the first pass:
   free, offline (satisfies the offline capture queue), instant. Server-side
   Deepgram/Whisper as fallback for long recordings and non-iOS later.
3. **OCR.** Don't buy one. Claude Opus 5 vision does description + text extraction in a
   single call; PDFs go in natively as `document` blocks (32MB / 600 pages). This
   collapses three spec line-items (§8.2 vision, OCR, scanned docs) into one call.

---

## 2. Repo layout

```
Boomy/
  backend/
    app/
      main.py                 # FastAPI app
      api/                    # routes: messages, attachments, memory, sync, export
      agent/
        runtime.py            # tool_runner loop
        tools.py              # the 8 memory tools (§5.4)
        prompts.py            # persona, tone-match, filing rules
      memory/
        store.py              # MemoryStore — the only thing that touches records
        search.py             # hybrid vector + keyword + recency/access boost
        buckets.py
        consolidation.py      # nightly job
      ingest/
        pipeline.py           # chunk / embed / extract
        extractors.py         # pdf, docx, txt, image, audio
      infra/                  # db, storage, embeddings
    migrations/               # alembic
    tests/
  ios/
    Boomy/
      Chat/                   # single-thread view + composer
      Memory/                 # bucket browser, fact editor
      Store/                  # MemoryStore protocol, GRDB cache, outbound queue
      Net/
```

---

## 3. Milestones

**M0 — Skeleton (foundation). ✅ DONE.** Postgres + pgvector + alembic; `memory_records`
and `buckets` tables per §5.2/§5.3; `MemoryStore` with write/read/revise/move; FastAPI
skeleton. Auth and S3 wiring deferred — nothing in M1 needs either, and the demo has a
single user. Verify: migrations round-trip, store invariants under test. ✅

**M1 — Memory layer (the product). ✅ DONE.** Embedder integration; hybrid search
(vector + `tsvector` keyword, RRF fusion, boost by recency and `access_count`, filter
`status='active'` and un-superseded); the 8 agent tools as `@beta_tool` functions;
session-start context builder (bucket index + core facts + last 3 episodes + system
buckets, <1000 tokens). Verify: seed a fixture corpus, assert fuzzy queries return the
right record. **This milestone is where recall quality is won or lost — build the eval
set here, before any UI exists.**

**M2 — Agent runtime. ✅ DONE** (pending a live-model pass). Tool runner loop; system prompt with cache breakpoint after
persona+tools (bucket index goes *after* the breakpoint — it's per-session volatile);
streaming responses; session boundaries (idle >30min / backgrounded >10min) and
end-of-session episode writing. Verify: scripted conversation captures and recalls.

**M3 — Capture pipeline. ✅ DONE.** Attachment upload → S3 → job queue; extractors per type;
~500-token overlapping chunks with parent linkage; Claude vision for images; optimistic
ack path. Verify: every attachment type round-trips — upload, extract, embed, and come
back out of `search()`. No latency assertions in this pass.

**M4 — iOS client.** Chat view (single thread, composer with text/mic/attachment);
`MemoryStore` protocol + GRDB cache + outbound queue with retry; streaming render.
Verify: airplane-mode capture syncs on reconnect.

**M5 — Browser & trust surface.** Bucket tree with counts/last-touched; item lists;
move/delete; "What I know about you" fact editor writing superseding records; export
(zip of JSON + files) and full delete. Verify: browser reflects DB exactly.

**M6 — Consolidation.** Nightly job (merge near-dupes, resolve contradictions by
recency, consolidate episodes, flag 90-day-stale, propose 60-day bucket retirement).
Verify: the job runs end-to-end and alters no `user_stated` fact (§12).

---

## 4. Schema refinements to §5.2

The spec's "active and no other active record supersedes them" requires a
self-join/anti-join on every read. Add a denormalized `superseded_by uuid NULL` column
alongside `supersedes`, maintained in the same transaction as `revise()`. Current belief
becomes `WHERE status='active' AND superseded_by IS NULL` — one partial index, no join.

Indexes: HNSW on `embedding`; partial B-tree on `(user_id, path)` where active;
GIN on `to_tsvector(content)`; B-tree on `last_accessed`.

Chunks: add `parent_id uuid NULL` (spec §6.2 implies it but the schema omits it).

---

## 5. Open issues / spec tensions to resolve

1. **"Never load full conversation history" (§5.5) vs. multi-turn coherence (§7).**
   Within a single session you still need the turns. Read as: never load *across*
   sessions. Confirm.
2. **Voice ordering.** On-device transcription means the client sends text, not audio —
   decide whether the audio artifact is also uploaded and stored (spec §5.1 lists voice
   notes as artifacts, which implies yes).
3. Unresolved from the spec itself: raw-transcript retention (proposal: 12 months) and
   upload limits (proposal: 25MB; PDF/DOCX/TXT/PNG/JPG/HEIC).

## 6. Cut for the demo pass

Both cuts are decisions, not oversights — record them so the eventual production pass
knows what it owes.

**Latency target (§4.1, §10, §12).** No 3s text ack, no 10s document ack. Consequences:
no fast mode; no split cheap-ack-plus-async-filing architecture — capture is one
streaming agentic turn that searches, files, and answers, taking as long as it takes;
no latency assertions in M3; the "% of captures acknowledged within 3s" secondary metric
in §10 is not instrumented. **The optimistic UI update stays** — the message still
appears in the thread immediately; only the agent's reply is unbounded. Worth watching
during the demo anyway: if a capture regularly takes 15s to acknowledge, the "texting a
person who is paying attention" feel is gone even without a formal SLA.

**Encryption at rest (§8.3).** No per-user keys, no envelope encryption, no KMS. Whatever
the managed Postgres and S3 give by default, nothing on top. This resolves the
encryption-vs-pgvector conflict by deferring it — `content`, `embedding`, and artifact
binaries all sit in the clear and are fully searchable. Consequences: no `infra/crypto`;
M6 loses its hardening half. **Two things to hold onto:** don't put the §8.3 privacy
claims in any demo-facing copy, and don't let real personal data into the demo instance —
the whole product invites users to dump their most personal material, and this build has
no story for protecting it. Export and full-delete (§4, §12) still ship in M5; they're
product surface, not security, and they're cheap.

## To Do Next

- **Grow the eval corpus before trusting any ranking constant.** It currently passes at
  1.00 on 12 records, which is too easy to discriminate. Add near-duplicates, distractors,
  superseded-vs-current pairs, and enough volume that `max_cosine_distance` (0.75),
  `recency_weight`, and `CANDIDATE_POOL` can be tuned against something real. Key is in
  backend/.env (gitignored).
- **Voyage free tier is 3 requests/minute** without a payment method. Fine for the eval
  and local use; add a card before M3 document ingestion (the 200M free tokens still
  apply either way).
- Next code: M4 — the iOS client (chat view, MemoryStore protocol, GRDB cache, outbound
  queue). Or M5's browser/export first if a UI for inspecting memory is more useful now.
- Voice is the one §3 capture type still unwired — it needs the transcription decision
  (on-device vs. server), which is now the only open dependency.
- Voyage is still on the free tier (3 req/min, confirmed by probe). Backoff now logs
  rather than sleeping silently, but ingestion is slow until a card is active.
- Transcription (on-device vs. server) is not needed until M3.
- Deferred and owed: auth and object storage (M3/M4, when attachments and a real client
  arrive), encryption and latency targets (before production at all).
- Before this ever leaves demo: encryption at rest (§6) and the latency targets (§6) are
  both owed back.
