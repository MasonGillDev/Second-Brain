"""
Configuration for the Second Brain AI Agent.
Tune these values to optimize performance vs. token cost.
"""

import os as _os

from keychain import get_secret as _get_secret

# Base directories
APP_DIR = _os.path.dirname(_os.path.abspath(__file__))
PROJECT_ROOT = _os.path.dirname(APP_DIR)

# =============================================================================
# MODEL SETTINGS
# =============================================================================

# Claude model to use for conversation
MODEL = "qwen/qwen3.5-397b-a17b"

# Model used for summarization (can use a cheaper/faster model to save cost)
SUMMARIZATION_MODEL = "claude-haiku-4-5-20251001"

# Max tokens for the agent's response.
# Must be large enough to fit tool-call arguments — long task prompts passed
# to code_task can exceed 1k tokens of JSON. Truncation here produces
# unterminated-string JSONDecodeErrors in the adapter.
MAX_RESPONSE_TOKENS = 8192

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
CHROMA_PERSIST_DIR = _os.path.join(APP_DIR, "memory", "data", "chroma")

# Number of results to retrieve per collection when building context
RETRIEVAL_TOP_K_LONG_TERM = 8
RETRIEVAL_TOP_K_EPISODIC = 2
RETRIEVAL_TOP_K_DOCUMENTS = 2
RETRIEVAL_TOP_K_PROCEDURAL = 5

# Procedures must be STRONGLY relevant — loosely-related recipes were getting
# injected as scaffolding and producing bad results, so this floor is set high
# (above long_term's) to admit only procedures that clearly match the request.
RETRIEVAL_MIN_RELEVANCE_PROCEDURAL = 0.6

# Minimum relevance score (0-1) to include a retrieved memory.
# Higher = stricter filtering = fewer but more relevant results = lower cost.
RETRIEVAL_MIN_RELEVANCE = 0.45

# Long-term memories get a stricter floor than the global default so only
# strongly-relevant facts are injected (less noise). Paired with a higher
# top_k (above) so that when several strongly-relevant facts exist, more of
# them make it in rather than being capped at 3.
RETRIEVAL_MIN_RELEVANCE_LONG_TERM = 0.55

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
DOCS_DIR = _os.path.join(APP_DIR, "memory", "docs")

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

# Documents require higher relevance to avoid injecting loosely-related content
RETRIEVAL_MIN_RELEVANCE_DOCUMENTS = 0.50

# Retrieval settings for code_context collection
RETRIEVAL_TOP_K_CODE = 12
RETRIEVAL_MIN_RELEVANCE_CODE = 0.40

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

# Per-model cost rates for accurate cost tracking
MODEL_COSTS = {
    "claude-sonnet-4-20250514":  {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
    "qwen/qwen3.5-397b-a17b":   {"input": 0.000532, "output": 0.0034},
}

# Token estimation multiplier: words * this = approx tokens
# Claude tokenizer averages ~1.3 tokens per word for English
TOKEN_ESTIMATION_MULTIPLIER = 1.3

# Log token usage to console (helps you see where tokens are going)
LOG_TOKEN_USAGE = True

# SQLite database for cost tracking and persistent logs
DB_PATH = _os.path.join(APP_DIR, "memory", "data", "secondbrain.db")

# Activity log retention: delete log entries older than this many days
LOG_RETENTION_DAYS = 3

# Max size (bytes) of a single expandable log detail blob (full tool args/result/reply)
LOG_DETAIL_MAX_BYTES = 256 * 1024

# =============================================================================
# SESSION PERSISTENCE
# =============================================================================

# File to save/restore conversation state (messages + rolling summary)
SESSION_FILE = _os.path.join(APP_DIR, "memory", "data", "session.json")

# Agent-editable personality file. The agent can update this to refine its own voice.
PERSONALITY_FILE = _os.path.join(APP_DIR, "memory", "data", "personality.txt")

# Cross-process cancel signal: agent writes this file, code_server subprocess polls it.
CANCEL_SIGNAL_FILE = _os.path.join(APP_DIR, "memory", "data", ".cancel_signal")

# Max characters for the personality block (keeps system prompt lean)
PERSONALITY_MAX_CHARS = 500

# =============================================================================
# TOOLS / MCP SERVERS
# =============================================================================

# Master switch for tool use
TOOLS_ENABLED = True

# Provider: "claude" or "openrouter"
LLM_PROVIDER = "openrouter"

# MCP servers to start. Each entry: server_name -> {command, args, env}
# These run as local subprocesses — nothing leaves your machine.
MCP_SERVERS = {
    
    "calendar": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "calendar_server.py")],
        "env": None,
    },
    "scheduler": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "scheduler_server.py")],
        "env": None,
    },
    "memory": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "memory_server.py")],
        "env": None,
    },
    "code": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "code_server.py")],
        "env": None,
    },
    "imessage": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "imessage_server.py")],
        "env": None,
    },
    "claude_hub": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "claude_hub_server.py")],
        "env": {"CLAUDE_HUB_URL": _os.environ.get("CLAUDE_HUB_URL", "http://localhost:3000")},
    },
    "fetch": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": ["-m", "mcp_server_fetch"],
        "env": None,
    },
    "music": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "music_server.py")],
        "env": None,
    },
    "lights": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "light_server.py")],
        "env": None,
    },
    "dashboards": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "dashboard_builder.py")],
        "env": None,
    },
    "toolgate": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "toolgate-mcp"),
        "args": [],
        "env": {
            # Secrets live in the macOS Keychain (see app/keychain.py), never in source.
            # Env var still wins if set, so deploys can override without Keychain.
            "TOOLGATE_API_KEY": _os.environ.get("TOOLGATE_API_KEY") or _get_secret("toolgate-api-key"),
            "TOOLGATE_BASE_URL": _os.environ.get("TOOLGATE_BASE_URL", "http://localhost:5050"),
            "TOOLGATE_AGENT_ID": _os.environ.get("TOOLGATE_AGENT_ID") or _get_secret("toolgate-agent-id"),
            "TOOLGATE_CREDENTIALS": _os.environ.get("TOOLGATE_CREDENTIALS", "{}"),
        },
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
    "claude_hub": "Observe and control your Claude Code sessions via Claude Hub — list projects/sessions, check which need attention, rename/flag them, and resume or start sessions in a terminal.",
    "imessage": "Read iMessage history — get recent messages, search conversations, check unread messages.",
    "fetch": "Fetch a URL and extract its contents as markdown. Read web pages, articles, and documentation.",
    "music": "Control Apple Music — play songs/artists/playlists, pause, skip, search library, get now playing, set volume.",
    "lights": "Control smart lights (Hue + Cync) — turn on/off, set brightness, change colors, activate scenes, control rooms. Light IDs are prefixed (hue:X, cync:X).",
    "dashboards": "Create, update, list, delete, and restore mini-dashboards. Uses Claude Code to build interactive web apps served at /d/<slug>/.",
}

# These servers' tools are ALWAYS sent without needing activation.
# Memory tools must always be available so the agent can store facts anytime.
ALWAYS_INCLUDE_SERVERS = ["memory", "toolgate"]

# Maximum tool-call rounds per user message (safety limit to prevent infinite loops)
MAX_TOOL_ROUNDS = 25

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
SLEEP_LOG_DIR = _os.path.join(APP_DIR, "memory", "data", "sleep_logs")

# Reference tier retrieval (added to auto-retrieval alongside long_term)
RETRIEVAL_TOP_K_REFERENCE = 3
RETRIEVAL_MIN_RELEVANCE_REFERENCE = 0.39

# =============================================================================
# RUNTIME OVERRIDES
# =============================================================================
# Load overrides from JSON file (set by dashboard config editor)
import json as _json
_overrides_path = _os.path.join(APP_DIR, "memory", "data", "config_overrides.json")


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
