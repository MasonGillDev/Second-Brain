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
from memory.conversation import ConversationMemory, estimate_tokens
from memory.vector_store import VectorStore
from memory.ingestion import ingest_documents
from memory.maintenance import MemoryMaintenance


def _build_skill_manifest() -> str:
    """Build the skill manifest block for the system prompt."""
    manifest = getattr(config, "SKILL_MANIFEST", {})
    if not manifest:
        return ""
    lines = []
    for name, desc in manifest.items():
        lines.append(f"- **{name}**: {desc}")
    skills_text = "\n".join(lines)
    return f"""

## Available Skills
You have access to specialized tool sets called "skills". To use one, call `activate_skill` with the skill name. Once activated, its tools become available for the rest of our conversation.

{skills_text}

Only activate skills when you need their tools. Memory tools are always available without activation."""


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
    from datetime import datetime
    now = datetime.now()
    skill_manifest = _build_skill_manifest() if config.TOOLS_ENABLED else ""
    personality = _load_personality()
    return f"""You are Second Brain, a general-purpose AI assistant with persistent memory and tool capabilities.
{personality}
Current date and time: {now.strftime("%A, %B %d, %Y at %I:%M %p")}.

You have access to several types of memory:
- **Working Memory**: The current conversation (recent messages)
- **Summary Memory**: A structured summary of earlier parts of our conversation
- **Long-Term Memory**: Persistent facts and knowledge stored across our interactions
- **Episodic Memory**: Records of specific past interactions and their outcomes
- **Procedural Memory**: Knowledge about how to perform specific tasks
- **Documents**: Reference material from ingested markdown files

You also have access to tools that let you interact with the filesystem and other services.
When a task requires reading files, listing directories, or other operations, use the available tools rather than asking the user to do it manually.
{skill_manifest}

## Response Style
- Be concise. Answer exactly what was asked, nothing more.
- Do not volunteer extra information the user didn't ask for.
- Do not editorialize, connect dots, or add commentary unless asked.
- Retrieved memories are context for YOU, not content to dump on the user.


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

Output a JSON array. Each item: {{"text": "standalone fact", "category": "user_fact|preference|decision|project_context"}}
If nothing passes the test, return: []"""


class MemoryManager:
    def __init__(self):
        self.conversation = ConversationMemory()
        self.vector_store = VectorStore()
        self._llm_client = anthropic.Anthropic()
        self.maintenance = MemoryMaintenance(self.vector_store, self._llm_client)
        self._exchange_count = 0
        self._ingest_docs_on_start()

    def _ingest_docs_on_start(self):
        """Ingest any new/changed docs at startup."""
        added = ingest_documents(self.vector_store)
        if added > 0 and config.LOG_TOKEN_USAGE:
            print(f"  [startup] Ingested {added} document chunks")

    def add_user_message(self, content: str):
        self.conversation.add_message("user", content)

    def add_assistant_message(self, content: str):
        self.conversation.add_message("assistant", content)
        self._exchange_count += 1

        # Run extraction every N exchanges
        if config.AUTO_EXTRACT_MEMORIES and self._exchange_count % config.EXTRACT_EVERY_N_EXCHANGES == 0:
            self.extract_memories()

        # Run consolidation every N exchanges
        if config.AUTO_EXTRACT_MEMORIES and self._exchange_count % config.CONSOLIDATE_EVERY_N_EXCHANGES == 0:
            self.consolidate_memories()

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

        # Format recent messages for the prompt
        msg_text = ""
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            msg_text += f"{role}: {msg['content']}\n\n"

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

    def retrieve_context(self, query: str) -> str:
        """Retrieve relevant memories from all collections for a query."""
        if not self._should_retrieve(query):
            if config.LOG_TOKEN_USAGE:
                print(f"  [retrieval] Skipped — trivial message")
            return ""

        sections = []

        # Long-term memories
        long_term = self.vector_store.query("long_term", query, top_k=config.RETRIEVAL_TOP_K_LONG_TERM)
        if long_term:
            items = "\n".join(f"- {m['text']}" for m in long_term)
            sections.append(f"### Relevant Knowledge\n{items}")

        # Episodic memories
        episodic = self.vector_store.query("episodic", query, top_k=config.RETRIEVAL_TOP_K_EPISODIC)
        if episodic:
            items = "\n".join(f"- {m['text']}" for m in episodic)
            sections.append(f"### Relevant Past Interactions\n{items}")

        # Procedural memories
        procedural = self.vector_store.query("procedural", query, top_k=config.RETRIEVAL_TOP_K_PROCEDURAL)
        if procedural:
            items = "\n".join(f"- {m['text']}" for m in procedural)
            sections.append(f"### Relevant Procedures\n{items}")

        # Document memories
        documents = self.vector_store.query("documents", query, top_k=config.RETRIEVAL_TOP_K_DOCUMENTS)
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
        """
        # Get retrieved memory context
        retrieved = self.retrieve_context(current_query)

        # Build system prompt with retrieved memories
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

            system += f"\n\n---\n## Retrieved Memories\n{retrieved}"

        # Get conversation context (summary + recent messages)
        messages = self.conversation.get_context()

        if config.LOG_TOKEN_USAGE:
            sys_tokens = estimate_tokens(system)
            msg_tokens = sum(estimate_tokens(m["content"]) for m in messages)
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
