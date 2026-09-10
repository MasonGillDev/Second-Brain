"""
Memory Manager - orchestrates all memory tiers.

Responsible for:
  - Managing conversation memory (working + summarized)
  - Retrieving relevant context from vector store
  - Building the full context payload sent to the LLM
  - Handling /remember, /forget, /episode, /procedure commands
"""

import json
import anthropic
import config
from keychain import get_secret
from memory.conversation import (ConversationMemory, estimate_tokens,
                                 _is_tool_message, _message_to_text)
from memory.vector_store import VectorStore
from memory.ingestion import ingest_documents
from memory.maintenance import MemoryMaintenance


def _build_skill_manifest() -> str:
    """All tools are exposed to the model at once now — there are no skills to
    activate, so the old manifest is replaced by a single standing note."""
    return ("\n\n## Tools\n"
            "Every tool you have is available to you right now — call tools "
            "directly. There are no skills to activate.")


def _load_personality() -> str:
    """Load the agent's personality from disk, if it exists."""
    import os
    path = getattr(config, "PERSONALITY_FILE", "")
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path) as f:
            text = f.read().strip()
        if text:
            return f"\n\n## Personality\n{text}"
    except Exception:
        pass
    return ""


def build_system_prompt() -> str:
    # NOTE: this prompt must stay byte-stable across turns — it is the first
    # block of every request, and any change invalidates the provider's prompt
    # cache for the entire request. Dynamic content (current date/time,
    # retrieved memories) is injected into the LAST user message instead
    # (see build_messages), where it can change freely without busting the
    # cached prefix. Do not add timestamps or per-turn content here.
    skill_manifest = _build_skill_manifest() if config.TOOLS_ENABLED else ""
    personality = _load_personality()
    return f"""You are Second Brain, a general-purpose AI assistant with persistent memory and tool capabilities.
{personality}
The current date and time are provided in the [Turn context] block of the latest user message.

You have access to several types of memory:
- **Working Memory**: The current conversation (recent messages)
- **Summary Memory**: A structured summary of earlier parts of our conversation
- **Long-Term Memory**: Persistent facts and knowledge stored across our interactions
- **Episodic Memory**: Records of specific past interactions and their outcomes
- **Procedural Memory**: Knowledge about how to perform specific tasks
- **Documents**: Reference material from ingested markdown files

You also have access to tools that let you interact with the filesystem and other services.
When a task requires reading files, listing directories, or other operations, use the available tools rather than asking the user to do it manually.

## Actions require tool calls — never fake them
You can only affect the real world (lights, music, TV, calendar, files, anything)
through tool calls. NEVER reply that an action is done unless you actually called
the tool for it in THIS turn and saw its result. If you are about to say "Done"
without having called a tool, stop and call the correct tool instead. If no
suitable tool exists or the call fails, tell the user plainly — never pretend.

## Procedures — the operating rule
EVERY task runs through a procedure. The "Procedure Index" in the latest user message's Retrieved Memories lists every saved procedure — before your first tool call on any task, decide which path you're on:
1. **An indexed procedure fits the request** → call `get_procedure("<name>")` and follow it exactly, step by step. It is the approved way — it encodes corrections and context that tool docs don't have. When a procedure references another ("Run procedure: <name>"), fetch that one with `get_procedure` and follow it inline.
2. **No indexed procedure fits** → you are in DISCOVERY. Call `get_procedure("create_procedure")` and follow it: it has you ask the user first, work the task out, and record a new procedure so path 1 handles this next time.

There is NO third path. Never improvise a multi-step task without a procedure — even when a perfectly-named tool looks like the obvious answer, the index comes first. Skipping the check because the task "seems obvious" is how mistakes repeat.

The ONLY things exempt from this rule: a single obvious tool call (turn on a light, one lookup), a quick factual answer, and plain conversation.

Procedures are saved and updated ONLY through the create_procedure flow — never call save_procedure ad hoc, and never save procedures for single-tool actions or one-off tasks.
{skill_manifest}

## Response Style
- Be concise. Answer exactly what was asked, nothing more.
- Do not volunteer extra information the user didn't ask for.
- Do not editorialize, connect dots, or add commentary unless asked.
- Retrieved memories are context for YOU, not content to dump on the user.
- IMPORTANT: Check the "Retrieved Memories" section in the latest user message's [Turn context] block BEFORE using search_memory. Only search if the answer is NOT already in the retrieved context.


## Personality
You have a personality description that shapes your voice and tone. You can view it with `get_personality` and evolve it with `update_personality` as you learn the user's preferences. Always read the current personality first before updating.

Do NOT use store_memory for:
- Things the user mentions casually in conversation
- Information that's only relevant right now
- Anything you've already stored (check with search_memory first if unsure)
- Conversation topics, questions, or requests

"""


EXTRACTION_PROMPT = """Extract ONLY durable facts from this conversation that would be useful in a conversation 2 weeks from now.

## What TO extract
- Identity: name, role, job title, company, team
- Lasting preferences: "prefers Go over Python", "likes terse responses"
- Technical stack/expertise: languages, frameworks, tools they use
- Ongoing projects: what they're building and why
- Explicit requests: "remember that I..." or "keep in mind..."
- Decisions with lasting impact: "we chose PostgreSQL over MongoDB"

## What NOT to extract — return [] instead
- What the user asked about in this conversation ("user asked about X")
- That the user is "aware of" or "interested in" something
- Anything the assistant said or suggested
- Questions, requests, or tasks from this session
- Anything that is only meaningful right now, not in 2 weeks
- Personality, tone, style, sarcasm, or communication preferences (these are stored separately in the personality file, not in memories)

## The test
For each candidate fact, ask: "If I told this to someone with no context, would it help them work with this user?" If no, skip it.

## Existing Memories (do not duplicate or rephrase these)
{existing_memories}

## Recent Messages
{messages}

Output a JSON array. Each item: {{"text": "standalone fact", "category": "user_fact|preference|decision|project_context|general|<custom>"}}
Use a custom category when the fact doesn't fit the standard ones (e.g., "health", "finance", "recipe", "contact").
If nothing passes the test, return: []"""


class MemoryManager:
    def __init__(self, session_file: str | None = None, threads: bool = False):
        self.conversation = ConversationMemory(session_file=session_file)
        self.vector_store = VectorStore()
        self._llm_client = anthropic.Anthropic(api_key=get_secret("anthropic-api-key"))
        self.maintenance = MemoryMaintenance(self.vector_store, self._llm_client)
        self._exchange_count = 0
        # Set when an extraction boundary is crossed; consumed by
        # run_deferred_maintenance() between turns.
        self._extraction_due = False
        self._ingest_docs_on_start()
        self._sync_seed_procedures()

        # Conversation threading (topic-scoped working memory). Per-instance
        # opt-in: only the dashboard agent passes threads=True.
        self.threads = None
        if threads and config.THREADS_MODE != "off":
            self.conversation.token_ceiling = config.THREAD_TOKEN_CEILING
            try:
                from memory.threads import ThreadManager
                self.threads = ThreadManager(self.vector_store, self.conversation)
                print(f"  [threads] enabled (mode={config.THREADS_MODE}, "
                      f"idle={config.THREAD_IDLE_TIMEOUT_MIN:.0f}m, "
                      f"ceiling={config.THREAD_TOKEN_CEILING}t)")
            except Exception as e:
                print(f"  [threads] init failed — threading disabled: {e}")
                self.conversation.token_ceiling = None

    def begin_turn(self, user_text: str) -> dict | None:
        """Thread lifecycle hook for the start of an LLM-path turn (park stale
        thread, route, resume/new). No-op (None) when threading is off."""
        if self.threads is None:
            return None
        return self.threads.begin_turn(user_text)

    def park_active_thread(self) -> None:
        """Park the live thread (shutdown hook). No-op when threading is off."""
        if self.threads is not None:
            self.threads.park_active()

    def cold_start(self) -> None:
        """The 'clear' operation. Under threading: park the current thread
        (kept + resumable) and start fresh — never deletes anything. Without
        threading: legacy behavior (wipe the single session). Blocking (park
        includes a Haiku title call) — invoke via asyncio.to_thread."""
        if self.threads is not None:
            self.threads.clear_active()
        else:
            self.conversation.clear_session()

    def _ingest_docs_on_start(self):
        """Ingest any new/changed docs at startup."""
        added = ingest_documents(self.vector_store)
        if added > 0 and config.LOG_TOKEN_USAGE:
            print(f"  [startup] Ingested {added} document chunks")

    def _sync_seed_procedures(self):
        """Re-sync the code-owned first-party procedures (create_procedure,
        create_workflow, create_trigger, ...) into procedural memory. Idempotent
        and non-fatal — every process that builds a MemoryManager re-syncs."""
        try:
            from memory.seed_procedures import sync_seed_procedures
            synced = sync_seed_procedures(self.vector_store)
            if synced and config.LOG_TOKEN_USAGE:
                print(f"  [startup] Synced {synced} first-party procedures")
        except Exception as e:
            print(f"  [startup] seed procedure sync skipped: {e}")

    def add_user_message(self, content: str):
        self.conversation.add_message("user", content)

    def add_assistant_message(self, content: str):
        self.conversation.add_message("assistant", content)
        self._exchange_count += 1

        # Extraction is a blocking LLM call, so it only gets FLAGGED here; the
        # agent runs it via run_deferred_maintenance() after the reply is out.
        if config.AUTO_EXTRACT_MEMORIES and self._exchange_count % config.EXTRACT_EVERY_N_EXCHANGES == 0:
            self._extraction_due = True

    def maintenance_due(self) -> bool:
        """True when between-turns maintenance (extraction/summarization) is pending."""
        return self._extraction_due or self.conversation.needs_summarization()

    def run_deferred_maintenance(self):
        """Run pending memory maintenance: extraction first (it reads the full
        buffer), then summarization (which trims it). Blocking — the agent calls
        this via asyncio.to_thread from a background task, serialized against
        turns by AgentCore's maintenance lock."""
        did_work = False
        if self._extraction_due:
            self._extraction_due = False
            self.extract_memories()
            did_work = True
        if self.conversation.needs_summarization():
            self.conversation.summarize_oldest()
            did_work = True
        if did_work:
            self.conversation.save_session()

    def remember(self, text: str, memory_type: str = "long_term", metadata: dict | None = None) -> str:
        """Store something in long-term memory (with dedup)."""
        meta = metadata or {}
        meta["type"] = memory_type
        result = self.maintenance.dedup_and_store(memory_type, text, meta)
        return result.get("id") or "skipped"

    def store_episode(self, summary: str, outcome: str, tags: list[str] | None = None):
        """Store an episodic memory."""
        text = f"Episode: {summary}\nOutcome: {outcome}"
        metadata = {"outcome": outcome}
        if tags:
            metadata["tags"] = ",".join(tags)
        self.vector_store.add("episodic", text, metadata)

    def store_procedure(self, name: str, description: str, steps: str):
        """Store a procedural memory."""
        text = f"Procedure: {name}\nDescription: {description}\nSteps:\n{steps}"
        metadata = {"name": name, "description": description}
        self.vector_store.add("procedural", text, metadata, doc_id=f"proc_{name}")

    def extract_memories(self):
        """Use LLM to extract memorable facts from recent conversation."""
        messages = self.conversation.messages
        if not messages:
            return

        # Format recent messages for the prompt. Tool machinery is skipped —
        # extraction wants durable user facts, not call/result noise.
        msg_text = ""
        for msg in messages:
            if _is_tool_message(msg):
                continue
            role = "User" if msg["role"] == "user" else "Assistant"
            msg_text += f"{role}: {_message_to_text(msg)}\n\n"

        # Get existing memories to avoid duplicates
        existing = ""
        existing_memories = self.vector_store.query("long_term", msg_text, top_k=10)
        if existing_memories:
            existing = "\n".join(f"- {m['text']}" for m in existing_memories)
        else:
            existing = "(none yet)"

        prompt = EXTRACTION_PROMPT.format(
            existing_memories=existing,
            messages=msg_text,
        )

        try:
            response = self._llm_client.messages.create(
                model=config.SUMMARIZATION_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            import db
            cost = db.compute_cost(config.SUMMARIZATION_MODEL, response.usage.input_tokens, response.usage.output_tokens)
            db.log_api_call("memory_extraction", config.SUMMARIZATION_MODEL,
                            response.usage.input_tokens, response.usage.output_tokens, cost)

            # Strip markdown code fences if present
            if raw.startswith("```"):
                # Remove ```json or ``` prefix and trailing ```
                lines = raw.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines).strip()

            # Extract the first JSON array from the response
            # (model may add reasoning text before or after)
            bracket_start = raw.find("[")
            bracket_end = raw.find("]", bracket_start) if bracket_start != -1 else -1
            if bracket_start != -1 and bracket_end != -1:
                raw = raw[bracket_start:bracket_end + 1]
            else:
                return  # No JSON array found

            # Parse JSON response
            memories = json.loads(raw)
            if not isinstance(memories, list):
                return

            stored = 0
            for mem in memories:
                if not isinstance(mem, dict) or "text" not in mem:
                    continue
                category = mem.get("category", "general")
                result = self.maintenance.dedup_and_store("long_term", mem["text"], {
                    "type": "auto_extracted",
                    "category": category,
                })
                if result["action"] != "SKIP":
                    stored += 1

            if stored > 0 and config.LOG_TOKEN_USAGE:
                print(f"  [extract] Auto-stored {stored} memories: {[m['text'][:50] for m in memories[:3]]}")

        except json.JSONDecodeError as e:
            if config.LOG_TOKEN_USAGE:
                print(f"  [extract] JSON parse failed: {e}")
                print(f"  [extract] Raw response: {raw[:200]}")
        except Exception as e:
            if config.LOG_TOKEN_USAGE:
                print(f"  [extract] Extraction failed: {e}")

    def _should_retrieve(self, query: str) -> bool:
        """Check if a message warrants memory retrieval."""
        normalized = query.strip().lower().rstrip("?!.")
        if normalized in config.RETRIEVAL_SKIP_PATTERNS:
            return False
        if len(query.split()) < config.RETRIEVAL_MIN_WORDS:
            return False
        return True

    def _procedure_index_section(self) -> str:
        """The full procedure index — name + trigger-condition description of
        EVERY saved procedure — injected into every non-trivial turn.

        Routing cannot depend on the model choosing to call list_procedures:
        tested three times, it reaches for the best-named task tool instead,
        every time. So the harness puts the choices in front of it and leaves
        only the fit-judgment to the model. Cheap at current scale; when the
        registry outgrows PROCEDURE_INDEX_MAX, replace this with real procedure
        retrieval (trigger-phrase aliases, like workflows)."""
        try:
            procs = self.vector_store.get_all("procedural", limit=500)
        except Exception:
            return ""
        entries = sorted(
            (p["metadata"]["name"], (p["metadata"].get("description") or "").strip())
            for p in procs if p["metadata"].get("name")
        )
        if not entries:
            return ""
        shown = entries[:config.PROCEDURE_INDEX_MAX]
        lines = "\n".join(f"- {name} — {desc}" for name, desc in shown)
        omitted = (f"\n(+{len(entries) - len(shown)} more — call list_procedures for the rest)"
                   if len(entries) > len(shown) else "")
        if config.LOG_TOKEN_USAGE:
            print(f"  [retrieval] Injected procedure index ({len(shown)} procedures)")
        return (
            "### Procedure Index (every saved procedure)\n"
            f"{lines}{omitted}\n"
            "If one fits this request: call get_procedure(\"<name>\") and follow it "
            "step by step BEFORE any other tool call. If none fits and the task "
            "needs more than a single obvious tool call: call "
            "get_procedure(\"create_procedure\") and follow it."
        )

    def retrieve_context(self, query: str) -> str:
        """Retrieve relevant memories from all collections for a query."""
        if not self._should_retrieve(query):
            if config.LOG_TOKEN_USAGE:
                print(f"  [retrieval] Skipped — trivial message")
            return ""

        sections = []

        # Procedure index FIRST — the routing layer. Always present so the model
        # never has to remember to go looking for it.
        proc_index = self._procedure_index_section()
        if proc_index:
            sections.append(proc_index)

        # Workflow triggers FIRST — the strongest signal. If the request matches a
        # saved workflow (by trigger phrase or description), the agent should RUN
        # the workflow rather than re-derive its steps by hand.
        try:
            wf_hits = self.vector_store.query(
                "workflows", query,
                top_k=config.RETRIEVAL_TOP_K_WORKFLOWS,
                min_relevance=config.RETRIEVAL_MIN_RELEVANCE_WORKFLOWS,
            )
        except Exception:
            wf_hits = []
        if wf_hits:
            # Many entries can point at one workflow (description + each trigger);
            # dedupe by workflow keeping the best score, then take the top 2.
            best: dict = {}
            for m in wf_hits:
                wname = m["metadata"].get("workflow")
                if wname and (wname not in best or m["relevance"] > best[wname]["relevance"]):
                    best[wname] = m
            top = sorted(best.values(), key=lambda m: -m["relevance"])[:2]
            try:
                import workflow_store as _wfs
                lines = []
                for m in top:
                    w = _wfs.get_workflow(m["metadata"]["workflow"])
                    if not w:
                        continue
                    params = ", ".join(p.get("name", "") for p in (w.get("params") or [])) or "none"
                    lines.append(f"- **{w['name']}** — {w.get('description', '')} (params: {params})")
                if lines:
                    sections.append(
                        "### Matching Workflows (run these instead of doing the steps manually)\n"
                        "The request matches saved workflows. Activate the `workflows` skill if needed, "
                        "then call `run_workflow` with the workflow_name (and params as a JSON string). "
                        "Do NOT recreate the workflow's steps with individual tools.\n" + "\n".join(lines)
                    )
                    if config.LOG_TOKEN_USAGE:
                        summary = [f"{m['metadata']['workflow']}@{m['relevance']}" for m in top]
                        print(f"  [retrieval] Injected workflows: {summary}")
            except Exception as e:
                if config.LOG_TOKEN_USAGE:
                    print(f"  [retrieval] workflow injection failed: {e}")

        # Procedural memories — these tell the model HOW to handle the request.
        procedural = self.vector_store.query(
            "procedural", query,
            top_k=config.RETRIEVAL_TOP_K_PROCEDURAL,
            min_relevance=config.RETRIEVAL_MIN_RELEVANCE_PROCEDURAL,
        )
        if procedural:
            items = "\n".join(f"- {m['text']}" for m in procedural)
            sections.append(f"### Relevant Procedures (follow these recipes when applicable)\n{items}")
            if config.LOG_TOKEN_USAGE:
                summary = [f"{m['metadata'].get('name', '?')}@{m['relevance']}" for m in procedural]
                print(f"  [retrieval] Injected procedures: {summary}")
        elif config.LOG_TOKEN_USAGE:
            # Diagnostic: show what was in the procedural collection but rejected.
            # Use a near-zero floor so we can see actual scores.
            raw = self.vector_store.query(
                "procedural", query,
                top_k=config.RETRIEVAL_TOP_K_PROCEDURAL,
                min_relevance=0.0,
            )
            if raw:
                summary = [f"{m['metadata'].get('name', '?')}@{m['relevance']}" for m in raw]
                print(f"  [retrieval] No procedures passed threshold {config.RETRIEVAL_MIN_RELEVANCE_PROCEDURAL}; top candidates: {summary}")

        # Long-term memories — stricter floor than the global default to keep
        # noise out, with a higher top_k so multiple strong matches can be kept.
        long_term = self.vector_store.query(
            "long_term", query,
            top_k=config.RETRIEVAL_TOP_K_LONG_TERM,
            min_relevance=config.RETRIEVAL_MIN_RELEVANCE_LONG_TERM,
        )
        if long_term:
            items = "\n".join(f"- {m['text']}" for m in long_term)
            sections.append(f"### Relevant Knowledge\n{items}")
            if config.LOG_TOKEN_USAGE:
                summary = [f"{m['relevance']}" for m in long_term]
                print(f"  [retrieval] Injected {len(long_term)} long-term memories @ scores: {summary}")
        elif config.LOG_TOKEN_USAGE:
            # Diagnostic: show top candidates that missed the threshold so the
            # floor can be tuned. Near-zero floor reveals actual scores.
            raw = self.vector_store.query(
                "long_term", query,
                top_k=config.RETRIEVAL_TOP_K_LONG_TERM,
                min_relevance=0.0,
            )
            if raw:
                summary = [f"{m['relevance']}" for m in raw]
                print(f"  [retrieval] No long-term memories passed threshold {config.RETRIEVAL_MIN_RELEVANCE_LONG_TERM}; top candidates: {summary}")

        # Episodic memories
        episodic = self.vector_store.query("episodic", query, top_k=config.RETRIEVAL_TOP_K_EPISODIC)
        if episodic:
            items = "\n".join(f"- {m['text']}" for m in episodic)
            sections.append(f"### Relevant Past Interactions\n{items}")

        # Reference memories (lower priority, higher threshold)
        reference = self.vector_store.query("reference", query, top_k=config.RETRIEVAL_TOP_K_REFERENCE)
        reference = [m for m in reference if m["relevance"] >= config.RETRIEVAL_MIN_RELEVANCE_REFERENCE]
        if reference:
            items = "\n".join(f"- {m['text']}" for m in reference)
            sections.append(f"### Reference Knowledge\n{items}")

        # Document memories (stricter threshold)
        documents = self.vector_store.query("documents", query, top_k=config.RETRIEVAL_TOP_K_DOCUMENTS)
        documents = [m for m in documents if m["relevance"] >= config.RETRIEVAL_MIN_RELEVANCE_DOCUMENTS]
        if documents:
            items = []
            for m in documents:
                source = m["metadata"].get("source_file", "unknown")
                items.append(f"- [{source}] {m['text'][:500]}")
            sections.append(f"### Relevant Documents\n" + "\n".join(items))

        return "\n\n".join(sections)

    def build_messages(self, current_query: str) -> tuple[str, list[dict]]:
        """
        Build the full message payload for the Claude API.
        Returns (system_prompt, messages).

        Cache discipline: the system prompt and prior messages form the stable,
        cacheable prefix. All per-turn dynamic content — current date/time and
        retrieved memories — rides in a [Turn context] block appended to a COPY
        of the last user message (the tail), so it never busts the cached prefix
        and never persists into conversation history.
        """
        from datetime import datetime

        # Get retrieved memory context
        retrieved = self.retrieve_context(current_query)

        # Stable system prompt (no per-turn content — see build_system_prompt)
        system = build_system_prompt()

        if retrieved:
            retrieved_tokens = estimate_tokens(retrieved)
            budget = int(config.TOTAL_CONTEXT_BUDGET * config.BUDGET_RETRIEVED_MEMORIES)

            # Trim retrieved context if it exceeds budget
            if retrieved_tokens > budget:
                # Rough trim by character ratio
                ratio = budget / retrieved_tokens
                trim_len = int(len(retrieved) * ratio)
                retrieved = retrieved[:trim_len] + "\n[...truncated]"

        # Get conversation context (summary + recent messages)
        messages = self.conversation.get_context()

        # Per-turn tail: date/time + retrieved memories, appended to a copy of
        # the final user message. get_context() returns references to the stored
        # message dicts — replace the list element with a copy so the injected
        # block is request-only and never saved to the session file.
        now = datetime.now()
        tail = f"\n\n[Turn context — current date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}."
        tail += " This block is injected context, not part of the user's message.]"
        if retrieved:
            tail += f"\n\n## Retrieved Memories\n{retrieved}"
        if messages and messages[-1].get("role") == "user" and isinstance(messages[-1].get("content"), str):
            messages[-1] = {**messages[-1], "content": messages[-1]["content"] + tail}

        if config.LOG_TOKEN_USAGE:
            sys_tokens = estimate_tokens(system)
            msg_tokens = sum(estimate_tokens(_message_to_text(m, full=True)) for m in messages)
            print(f"  [context] system: ~{sys_tokens}t | messages: ~{msg_tokens}t | total: ~{sys_tokens + msg_tokens}t")

        return system, messages

    def consolidate_memories(self) -> dict:
        """Run memory consolidation."""
        return self.maintenance.consolidate("long_term")

    def ingest_docs(self) -> int:
        """Re-scan and ingest documents."""
        return ingest_documents(self.vector_store)

    def get_stats(self) -> dict:
        return {
            "conversation": self.conversation.get_stats(),
            "vector_store": self.vector_store.get_stats(),
        }
