"""
Configuration for the Second Brain AI Agent.
Tune these values to optimize performance vs. token cost.
"""

# =============================================================================
# MODEL SETTINGS
# =============================================================================

# Claude model to use for conversation
MODEL = "claude-sonnet-4-20250514"

# Model used for summarization (can use a cheaper/faster model to save cost)
SUMMARIZATION_MODEL = "claude-haiku-4-5-20251001"

# Max tokens for the agent's response
MAX_RESPONSE_TOKENS = 1024

# =============================================================================
# CONTEXT WINDOW BUDGET
# =============================================================================
# Total token budget for what we send to the API per request.
# Lower this to reduce cost per message. Raise it for richer context.
# Claude Sonnet supports 200k, but you pay per token — no need to fill it.

TOTAL_CONTEXT_BUDGET = 16000  # tokens (good balance of cost vs. context)

# How the budget is split (must sum to 1.0):
BUDGET_SYSTEM_PROMPT = 0.15       # System prompt + procedural memory
BUDGET_SUMMARY = 0.20             # Rolling conversation summary
BUDGET_RETRIEVED_MEMORIES = 0.15  # Vector DB retrievals (long-term, episodic, docs)
BUDGET_WORKING_MEMORY = 0.50      # Recent messages (the live conversation)

# =============================================================================
# CONVERSATION / SUMMARIZATION
# =============================================================================

# Number of recent messages to always keep in working memory (never summarized)
WORKING_MEMORY_MIN_MESSAGES = 5

# How many messages to accumulate before triggering a summarization pass
SUMMARIZE_EVERY_N_MESSAGES = 15

# Max tokens for the rolling summary itself
MAX_SUMMARY_TOKENS = int(TOTAL_CONTEXT_BUDGET * BUDGET_SUMMARY)

# =============================================================================
# VECTOR STORE / RETRIEVAL
# =============================================================================

# ChromaDB persistent storage path
CHROMA_PERSIST_DIR = "./memory/data/chroma"

# Number of results to retrieve per collection when building context
RETRIEVAL_TOP_K_LONG_TERM = 3
RETRIEVAL_TOP_K_EPISODIC = 2
RETRIEVAL_TOP_K_DOCUMENTS = 3
RETRIEVAL_TOP_K_PROCEDURAL = 2

# Minimum relevance score (0-1) to include a retrieved memory.
# Higher = stricter filtering = fewer but more relevant results = lower cost.
RETRIEVAL_MIN_RELEVANCE = 0.3

# Minimum word count in a user message to trigger memory retrieval.
# Short messages like "yes", "ok", "thanks" skip retrieval entirely to save tokens.
RETRIEVAL_MIN_WORDS = 2

# Messages matching these patterns skip retrieval regardless of length.
RETRIEVAL_SKIP_PATTERNS = [
    "yes", "no", "ok", "okay", "sure", "thanks", "thank you", "got it",
    "yep", "nope", "agreed", "right", "correct", "exactly", "perfect",
    "go ahead", "do it", "sounds good", "makes sense", "never mind",
]

# =============================================================================
# DOCUMENT INGESTION
# =============================================================================

# Where to watch for markdown files to ingest
DOCS_DIR = "./memory/docs"

# Chunk size for splitting documents (in characters)
CHUNK_SIZE = 1000

# Overlap between chunks (helps preserve context at boundaries)
CHUNK_OVERLAP = 200

# =============================================================================
# CODE INGESTION
# =============================================================================

# Minimum character length for a comment to be worth storing
CODE_INGEST_MIN_COMMENT_LENGTH = 20

# Minimum consecutive comment lines to form a "block" worth storing
CODE_INGEST_MIN_COMMENT_LINES = 2

# Max file size to ingest (skip huge generated files)
CODE_INGEST_MAX_FILE_SIZE = 100_000  # 100KB

# Retrieval settings for code_context collection
RETRIEVAL_TOP_K_CODE = 3
RETRIEVAL_MIN_RELEVANCE_CODE = 0.38

# =============================================================================
# MEMORY IMPORTANCE
# =============================================================================

# Threshold for auto-storing conversation turns as long-term memories.
# The agent uses the LLM to score importance 0-1.
# Higher = fewer things stored = lower cost, but less recall.
IMPORTANCE_THRESHOLD = 0.5

# Whether to use the LLM to auto-extract memories from conversation.
# Runs every EXTRACT_EVERY_N_EXCHANGES exchanges + on quit.
# Uses SUMMARIZATION_MODEL (Haiku) to keep cost low.
AUTO_EXTRACT_MEMORIES = True

# How often to run extraction (in exchanges — 1 exchange = user msg + assistant reply)
EXTRACT_EVERY_N_EXCHANGES = 7

# =============================================================================
# MEMORY MAINTENANCE (dedup + consolidation)
# =============================================================================

# Dedup: how many similar memories to compare against before storing
DEDUP_TOP_K = 3

# Dedup: minimum relevance score to consider a memory a potential duplicate
DEDUP_MIN_RELEVANCE = 0.5

# Consolidation: how often to run (in exchanges)
CONSOLIDATE_EVERY_N_EXCHANGES = 100

# Consolidation: also run on shutdown
CONSOLIDATE_ON_SHUTDOWN = False

# Consolidation: max memories to process in one batch (cost safety valve)
CONSOLIDATION_BATCH_LIMIT = 100

# Consolidation: similarity threshold for grouping (0-1, higher = stricter)
CONSOLIDATION_SIMILARITY_THRESHOLD = 0.7

# Consolidation: max memories per cluster (prevents over-merging)
CONSOLIDATION_MAX_CLUSTER_SIZE = 2

# =============================================================================
# COST CONTROLS
# =============================================================================

# Approximate token-to-dollar rates (for logging/awareness, not enforcement)
INPUT_COST_PER_1K = 0.003    # $/1K input tokens (Sonnet)
OUTPUT_COST_PER_1K = 0.015   # $/1K output tokens (Sonnet)

# Token estimation multiplier: words * this = approx tokens
# Claude tokenizer averages ~1.3 tokens per word for English
TOKEN_ESTIMATION_MULTIPLIER = 1.3

# Log token usage to console (helps you see where tokens are going)
LOG_TOKEN_USAGE = True

# =============================================================================
# SESSION PERSISTENCE
# =============================================================================

# File to save/restore conversation state (messages + rolling summary)
SESSION_FILE = "./memory/data/session.json"

# Agent-editable personality file. The agent can update this to refine its own voice.
PERSONALITY_FILE = "./memory/data/personality.txt"

# Max characters for the personality block (keeps system prompt lean)
PERSONALITY_MAX_CHARS = 500

# =============================================================================
# TOOLS / MCP SERVERS
# =============================================================================

# Master switch for tool use
TOOLS_ENABLED = True

# Provider: "claude" or "openai"
LLM_PROVIDER = "claude"

# MCP servers to start. Each entry: server_name -> {command, args, env}
# These run as local subprocesses — nothing leaves your machine.
MCP_SERVERS = {
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "./SecondBrainSandBox"],
        "env": None,
    },
    "calendar": {
        "command": "./venv/bin/python",
        "args": ["./mcp_servers/calendar_server.py"],
        "env": None,
    },
    "scheduler": {
        "command": "./venv/bin/python",
        "args": ["./mcp_servers/scheduler_server.py"],
        "env": None,
    },
    "memory": {
        "command": "./venv/bin/python",
        "args": ["./mcp_servers/memory_server.py"],
        "env": None,
    },
    "code": {
        "command": "./venv/bin/python",
        "args": ["./mcp_servers/code_server.py"],
        "env": None,
    },
    "imessage": {
        "command": "./venv/bin/python",
        "args": ["./mcp_servers/imessage_server.py"],
        "env": None,
    },
    "fetch": {
        "command": "./venv/bin/python",
        "args": ["-m", "mcp_server_fetch"],
        "env": None,
    },
    "music": {
        "command": "./venv/bin/python",
        "args": ["./mcp_servers/music_server.py"],
        "env": None,
    },
}

# Allowlist of tools per server. Only these tools get exposed to the model.
# Use the tool name WITHOUT the server prefix (e.g., "read_file" not "filesystem__read_file").
# Set to None or omit the server to allow ALL tools from that server.
TOOL_ALLOWLIST = {
    "filesystem": [
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "search_files",
        "directory_tree",
    ],
    # "calendar": None,  # None = all tools allowed (default)
}

# Skill manifest: lightweight descriptions shown in the system prompt.
# The agent calls `activate_skill` to load the full tool definitions on demand.
# Servers listed in ALWAYS_INCLUDE_SERVERS are excluded (always available).
SKILL_MANIFEST = {
    "filesystem": "Read, write, edit, and search files and directories on the local machine.",
    "calendar": "View and manage Google Calendar events (create, list, search, update, delete).",
    "scheduler": "Create and manage recurring scheduled tasks (cron-like jobs, daily reminders).",
    "code": "Delegate coding tasks to Claude Code — research codebases, write/edit code, and manage background processes (start/stop dev servers, etc.).",
    "imessage": "Read iMessage history — get recent messages, search conversations, check unread messages.",
    "fetch": "Fetch a URL and extract its contents as markdown. Read web pages, articles, and documentation.",
    "music": "Control Apple Music — play songs/artists/playlists, pause, skip, search library, get now playing, set volume.",
}

# These servers' tools are ALWAYS sent without needing activation.
# Memory tools must always be available so the agent can store facts anytime.
ALWAYS_INCLUDE_SERVERS = ["memory"]

# Maximum tool-call rounds per user message (safety limit to prevent infinite loops)
MAX_TOOL_ROUNDS = 7

# Telegram user ID for scheduled task notifications
TELEGRAM_NOTIFY_USER_ID = 6080568335

# =============================================================================
# SLEEP AGENT (memory consolidation)
# =============================================================================

# Master toggle
SLEEP_AGENT_ENABLED = True

# Model — Haiku keeps costs low for reorganization work
SLEEP_MODEL = SUMMARIZATION_MODEL

# Recursive similarity search
SLEEP_SEARCH_DEPTH = 3               # max hops from each seed memory
SLEEP_SIMILARITY_DECAY = 0.85        # relevance *= this per depth level
SLEEP_TOP_K_PER_HOP = 5              # results per query at each depth
SLEEP_MIN_RELEVANCE = 0.25           # minimum effective relevance after decay
SLEEP_MAX_CONTEXT_MEMORIES = 35      # hard cap on memories sent to LLM
SLEEP_MAX_DOCUMENT_MEMORIES = 5      # hard cap on read-only document chunks
SLEEP_MIN_DOCUMENT_RELEVANCE = 0.45  # documents must be highly relevant
SLEEP_SEED_LOOKBACK_HOURS = 24       # "today" = memories from last N hours
SLEEP_MAX_SEEDS = 15                 # max seed memories to start from

# Agent loop
SLEEP_MAX_TOOL_ROUNDS = 15           # max LLM rounds per run
SLEEP_MAX_LLM_CALLS = 20             # hard cap on total API calls

# Logging
SLEEP_LOG_DIR = "./memory/data/sleep_logs"

# Reference tier retrieval (added to auto-retrieval alongside long_term)
RETRIEVAL_TOP_K_REFERENCE = 3
RETRIEVAL_MIN_RELEVANCE_REFERENCE = 0.39

# =============================================================================
# RUNTIME OVERRIDES
# =============================================================================
# Load overrides from JSON file (set by dashboard config editor)
import os as _os
import json as _json
_overrides_path = "./memory/data/config_overrides.json"


def reload_overrides():
    """Re-read config overrides from disk. Called before each message."""
    if _os.path.exists(_overrides_path):
        try:
            with open(_overrides_path) as f:
                for k, v in _json.load(f).items():
                    if k.isupper():
                        globals()[k] = v
        except (_json.JSONDecodeError, OSError):
            pass


# Load on import
reload_overrides()
