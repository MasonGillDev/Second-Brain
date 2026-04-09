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
SUMMARIZE_EVERY_N_MESSAGES = 8

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
RETRIEVAL_MIN_RELEVANCE = 0.5

# Minimum word count in a user message to trigger memory retrieval.
# Short messages like "yes", "ok", "thanks" skip retrieval entirely to save tokens.
RETRIEVAL_MIN_WORDS = 3

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
DEDUP_MIN_RELEVANCE = 0.35

# Consolidation: how often to run (in exchanges)
CONSOLIDATE_EVERY_N_EXCHANGES = 25

# Consolidation: also run on shutdown
CONSOLIDATE_ON_SHUTDOWN = True

# Consolidation: max memories to process in one batch (cost safety valve)
CONSOLIDATION_BATCH_LIMIT = 100

# Consolidation: similarity threshold for grouping (0-1, higher = stricter)
CONSOLIDATION_SIMILARITY_THRESHOLD = 0.45

# Consolidation: max memories per cluster (prevents over-merging)
CONSOLIDATION_MAX_CLUSTER_SIZE = 5

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
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "./"],
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

# Keyword routing: maps keywords in user messages to MCP server names.
# Only tool definitions from matched servers get sent to the model.
# If no keywords match, no tools are sent (saves tokens on casual chat).
# Keywords are matched case-insensitively against the user's message.
TOOL_ROUTING = {
    "filesystem": [
        "file", "files", "read", "write", "create file", "edit", "directory",
        "folder", "list files", "save", "open", "path", "config", ".py", ".md",
        ".json", ".txt", ".js", ".ts", "code", "script", "source",
    ],
    "calendar": [
        "calendar", "event", "events", "meeting", "appointment",
        "tomorrow", "today", "this week", "next week", "busy", "free",
        "agenda", "when am i", "what's on", "whats on",
    ],
    "scheduler": [
        "schedule", "cron", "scheduled", "every day", "every morning",
        "every hour", "recurring", "remind me", "daily", "weekly",
        "set up a task", "automated", "run every", "at 8am", "at 9am",
    ],
    # Memory tools are always included (see ALWAYS_INCLUDE_SERVERS below)
}

# These servers' tools are ALWAYS sent, regardless of keyword routing.
# Memory tools must always be available so the agent can store facts anytime.
ALWAYS_INCLUDE_SERVERS = ["memory"]

# Maximum tool-call rounds per user message (safety limit to prevent infinite loops)
MAX_TOOL_ROUNDS = 7

# Telegram user ID for scheduled task notifications
TELEGRAM_NOTIFY_USER_ID = 6080568335
