"""
Configuration for the Second Brain AI Agent.
Tune these values to optimize performance vs. token cost.
"""

import os as _os

from keychain import get_secret as _get_secret


def _secret_or_none(name: str) -> str:
    """Keychain lookup that returns '' instead of raising when the secret is
    absent — lets optional integrations (e.g. Composio before it's configured)
    avoid crashing config import."""
    try:
        return _get_secret(name)
    except Exception:
        return ""


# Base directories
APP_DIR = _os.path.dirname(_os.path.abspath(__file__))
PROJECT_ROOT = _os.path.dirname(APP_DIR)

# Load secrets/config from the project-root .env (gitignored) BEFORE any
# os.environ reads below. Real environment vars always win (override=False), so
# .env is a fallback — handy on a headless box where the Keychain is locked.
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(_os.path.join(PROJECT_ROOT, ".env"))
except Exception:
    pass  # dotenv optional; env vars / Keychain still work without it

# =============================================================================
# MODEL SETTINGS
# =============================================================================

# Model to use for conversation
MODEL = "minimax/minimax-m3"

# Preferred OpenRouter providers, in order. Pinned so the prompt-cache actually
# hits: the KV cache is provider-local, and default load-balancing scatters
# consecutive requests across providers. Empty list = default routing.
#
# The pin is model-specific — re-check endpoints when MODEL changes. Names are
# case-sensitive ("Minimax" binds, "MiniMax" 404s) and an unknown name is
# silently ignored rather than rejected, so a typo degrades to default routing
# and the cache locality is quietly lost. Verify a new pin with
# allow_fallbacks=False: a valid name routes, an invalid one 404s.
#
# Novita and AtlasCloud do NOT support tool calling for minimax-m3. AtlasCloud
# is otherwise the fastest endpoint (105 tps) and tempting to pin — but since
# nearly every brain request carries tools, OpenRouter drops it from the
# candidate set and we fall through to default routing, so the pin buys nothing.
# MiniMax first-party wins on what actually matters: 1.44s TTFT (vs AtlasCloud's
# 1.46s), 99.63% uptime, plus tools and cache reads. Avoid Parasail (12.3s TTFT,
# 84.5% uptime) and DeepInfra (8.9s). Provider stats read 2026-07-09.
OPENROUTER_PROVIDER_ORDER = [
    p for p in _os.environ.get("OPENROUTER_PROVIDER_ORDER", "Minimax").split(",") if p
]

# Per-MODEL provider pin. The pin MUST follow the model: a provider that serves
# one model without tool-calling serves another WITH it (e.g. Novita has no tools
# for minimax-m3 but does for glm-5.2), so a single global pin is wrong the moment
# MODEL changes. The adapter looks up the current model here; a model not listed
# falls back to OPENROUTER_PROVIDER_ORDER, then to default routing. This is what
# makes switching MODEL live from the dashboard keep correct caching + tools.
# Pins are the cheapest endpoint serving the model with tools + prompt caching.
# Endpoints/prices read 2026-07-15; re-verify with allow_fallbacks=False.
MODEL_PROVIDER_PINS = {
    "minimax/minimax-m3": ["Minimax"],
    # Novita + StreamLake: cheapest glm-5.2 endpoints with tools, 1M ctx, cache
    # ($0.86/$2.71, cache $0.16). Note Novita — unusable for minimax-m3 (no tools)
    # — is fully tool-capable here, exactly why the pin is per-model.
    "z-ai/glm-5.2": ["Novita", "StreamLake"],
}

# Curated models shown in the dashboard model picker (you can still type any
# OpenRouter id). Add a MODEL_PROVIDER_PINS entry when caching matters for one.
MODEL_PRESETS = [
    "z-ai/glm-5.2",          # #1 open-weight on the AA Intelligence Index (51)
    "minimax/minimax-m3",    # prior default — cheap, 1M ctx
    "z-ai/glm-4.7",          # cheaper GLM, still frontier-class
    "deepseek/deepseek-v3.2",  # cheapest strong option
]

# Fast-path intent router: match simple commands ("pause the music", "lights
# off") by embedding similarity and call the tool directly, skipping the LLM.
# THRESHOLD is the min relevance (1/(1+L2 distance)) to fire — higher = stricter
# (fewer false tool calls, more falls-through to the LLM). Tuned empirically.
FAST_INTENT_ENABLED = _os.environ.get("FAST_INTENT_ENABLED", "1") not in ("0", "false", "False")
FAST_INTENT_THRESHOLD = float(_os.environ.get("FAST_INTENT_THRESHOLD", "0.60"))

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

# Working memory holds whole TURNS verbatim — including tool calls and their
# results — so the model keeps its own recent tool activity in context.
# Compaction folds the OLDEST turns into the rolling summary when the buffer's
# estimated tokens exceed this budget; a turn is never split.
WORKING_MEMORY_TOKEN_BUDGET = int(TOTAL_CONTEXT_BUDGET * BUDGET_WORKING_MEMORY)

# The newest N turns are always kept verbatim, even over budget.
WORKING_MEMORY_MIN_TURNS = 3

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

# Workflow auto-injection: user requests are matched against each workflow's
# trigger phrases + description (the 'workflows' chroma collection, synced by
# workflow_store). Trigger phrases embed in the same register as real requests,
# so true matches score well above this floor while unrelated chatter stays under.
RETRIEVAL_TOP_K_WORKFLOWS = 5
RETRIEVAL_MIN_RELEVANCE_WORKFLOWS = 0.55

# Procedures must be STRONGLY relevant — loosely-related recipes were getting
# injected as scaffolding and producing bad results, so this floor is set high
# (above long_term's) to admit only procedures that clearly match the request.
RETRIEVAL_MIN_RELEVANCE_PROCEDURAL = 0.6

# The full procedure index (name + description of EVERY saved procedure) is
# injected into every non-trivial turn — routing is the harness's job, the
# model only judges fit (semantic thresholds proved unable to carry routing:
# real requests scored 0.33-0.45 against the 0.6 floor). Past this cap the
# index truncates and points at list_procedures; hitting it regularly is the
# signal to build real procedure retrieval (trigger aliases).
PROCEDURE_INDEX_MAX = 60

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
EXTRACT_EVERY_N_EXCHANGES = 10

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

# ── Conversation threading (topic-scoped working memory) ─────────────
# After an idle gap, the next prompt either resumes the matching past thread
# (with its context) or starts a fresh one. Modes:
#   off    — single endless session (legacy behavior)
#   shadow — idle-parking live; routing decisions LOGGED only (always a fresh
#            thread after idle) so THREAD_RESUME_THRESHOLD can be tuned on
#            real usage before it controls behavior
#   on     — full resume behavior
THREADS_MODE = _os.environ.get("THREADS_MODE", "on")
THREADS_DIR = _os.path.join(APP_DIR, "memory", "data", "threads")
THREAD_IDLE_TIMEOUT_MIN = float(_os.environ.get("THREAD_IDLE_TIMEOUT_MIN", "45"))
# Per-thread verbatim context ceiling (tokens). In-thread summarization
# switches from the >20-message trigger to this token trigger, so threads can
# actually hold deep context. 15k ≈ 60-150 turns; cold resume prefill ~2-3s.
THREAD_TOKEN_CEILING = int(_os.environ.get("THREAD_TOKEN_CEILING", "15000"))
# Min blended similarity (0.6*messages + 0.4*summary) to resume a thread.
# Tuned from observed scores (2026-07-08): on-topic vs pure threads 0.494-0.572,
# off-topic never above 0.43 — 0.47 splits with margin both ways.
THREAD_RESUME_THRESHOLD = float(_os.environ.get("THREAD_RESUME_THRESHOLD", "0.47"))
# Max non-archived threads kept in the routing index; oldest are archived
# (embeddings removed, file kept on disk).
THREAD_MAX_ACTIVE = int(_os.environ.get("THREAD_MAX_ACTIVE", "20"))

# Agent-editable personality file. The agent can update this to refine its own voice.
PERSONALITY_FILE = _os.path.join(APP_DIR, "memory", "data", "personality.txt")

# Cross-process cancel signal: agent writes this file, code_server subprocess polls it.
CANCEL_SIGNAL_FILE = _os.path.join(APP_DIR, "memory", "data", ".cancel_signal")

# Scheduled tasks store — the JSON the scheduler daemon (agent/scheduler.py) and
# the scheduler MCP server read/write. The internal calendar also writes here to
# register one-time event reminders, so they share one canonical path.
SCHEDULED_TASKS_FILE = _os.path.join(APP_DIR, "memory", "data", "scheduled_tasks.json")

# Workflow registry — named, parameterized, composable routines that the agent
# authors (via the workflows MCP server) and both the agent and the scheduler
# can run. See workflow_store.py / workflow_runner.py.
WORKFLOWS_FILE = _os.path.join(APP_DIR, "memory", "data", "workflows.json")

# Trigger registry — event-driven automations (webhooks + pollers) that run a
# workflow or agent prompt when something happens. See trigger_store.py /
# trigger_engine.py. Contains per-trigger webhook secrets; the directory is
# git-ignored.
TRIGGERS_FILE = _os.path.join(APP_DIR, "memory", "data", "triggers.json")

# Base URL other devices use to reach webhook triggers (tailnet MagicDNS name).
# Override if the tailnet needs the full *.ts.net hostname (e.g. on iOS).
PUBLIC_BASE_URL = _os.environ.get("SECOND_BRAIN_PUBLIC_URL", "http://masons-mac-mini:5001")

# Granularity of the poll-source loop (seconds between due-checks; each poll
# trigger's own interval_seconds controls how often it actually fetches).
TRIGGER_POLL_TICK_SECONDS = 15

# Pending iMessage reply watches (see app/reply_watch.py). A watch waits for a
# named contact to answer a question the agent asked, then wakes the agent with
# the reply. SETTLE lets a burst of texts finish before acting — people send
# "let me check" and the real answer a minute apart.
REPLY_WATCH_POLL_SECONDS = 20
REPLY_WATCH_SETTLE_SECONDS = 45
REPLY_WATCH_EXPIRE_HOURS = 24

# Proactive calendar heads-ups (see app/calendar_briefing.py). The planner decides
# which upcoming events deserve a spoken nudge and how far ahead. It re-plans when
# the schedule changes rather than on a timer, so CHECK_SECONDS is a cheap SQLite
# read, not an LLM call.
BRIEFING_WINDOW_HOURS = 18
BRIEFING_CHECK_SECONDS = 300
BRIEFING_MAX_PLAN_AGE_HOURS = 6
# Announce every timed event at its start ("it's time"), separate from the
# planner's advance heads-ups. All-day events are excluded.
BRIEFING_ANNOUNCE_AT_START = True

# Max characters for the personality block (keeps system prompt lean)
PERSONALITY_MAX_CHARS = 500

# =============================================================================
# TOOLS / MCP SERVERS
# =============================================================================

# Master switch for tool use
TOOLS_ENABLED = True

# Where non-dashboard processes (telegram, scheduler) reach the dashboard's
# toolbus API. Only the dashboard spawns MCP_SERVERS below; everyone else
# proxies tool calls here so one instance of each server exists machine-wide.
TOOLBUS_URL = _os.environ.get("TOOLBUS_URL", "http://127.0.0.1:5001")

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
    # System admin: delegates OS/machine administration to a gated Claude Code
    # (read-mostly, asks before changing anything, resumable). See system_server.py.
    "system": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "system_server.py")],
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
        "env": {"CYNC_STATE_TIMEOUT": _os.environ.get("CYNC_STATE_TIMEOUT", "2.5")},
    },
    "tv": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "tv_server.py")],
        "env": None,
    },
    "windows": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "windows_server.py")],
        "env": None,
    },
    "dashboards": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "dashboard_builder.py")],
        "env": None,
    },
    # Named, composable multi-step routines. The agent authors/runs them here;
    # the scheduler reuses the same runner (workflow_runner.py) to fire them by name.
    "workflows": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "workflows_server.py")],
        "env": None,
    },
    "triggers": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "triggers_server.py")],
        "env": None,
    },
    # --- DISABLED 2026-06-23: the agent-facing ToolGate MCP server is turned off
    # in favor of Composio (see the "composio" server below). Code preserved, not
    # deleted — to re-enable, uncomment this block AND re-add "toolgate" to
    # ALWAYS_INCLUDE_SERVERS. NOTE: the `projects` server below still uses ToolGate
    # internally (its own TOOLGATE_* env, hitting the REST API at :5050) for GitHub
    # data — that path is intentionally left intact.
    # "toolgate": {
    #     "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "toolgate-mcp"),
    #     "args": [],
    #     "env": {
    #         # Secrets live in the macOS Keychain (see app/keychain.py), never in source.
    #         # Env var still wins if set, so deploys can override without Keychain.
    #         "TOOLGATE_API_KEY": _os.environ.get("TOOLGATE_API_KEY") or _get_secret("toolgate-api-key"),
    #         "TOOLGATE_BASE_URL": _os.environ.get("TOOLGATE_BASE_URL", "http://localhost:5050"),
    #         "TOOLGATE_AGENT_ID": _os.environ.get("TOOLGATE_AGENT_ID") or _get_secret("toolgate-agent-id"),
    #         "TOOLGATE_CREDENTIALS": _os.environ.get("TOOLGATE_CREDENTIALS", "{}"),
    #     },
    # },
    "composio": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "composio_server.py")],
        "env": {
            # Composio API key: env wins, else macOS Keychain ('composio-api-key').
            "COMPOSIO_API_KEY": _os.environ.get("COMPOSIO_API_KEY") or _secret_or_none("composio-api-key"),
            # Single-user agent — all Composio app connections are scoped to this id.
            "COMPOSIO_USER_ID": _os.environ.get("COMPOSIO_USER_ID", "default"),
        },
    },
    "projects": {
        "command": _os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
        "args": [_os.path.join(APP_DIR, "mcp_servers", "projects_server.py")],
        "env": {
            "CLAUDE_HUB_URL": _os.environ.get("CLAUDE_HUB_URL", "http://localhost:3000"),
            # _secret_or_none (not _get_secret) so a locked/absent Keychain on a
            # headless box can't crash config import; falls back to "" and the
            # projects ToolGateClient degrades gracefully.
            "TOOLGATE_API_KEY": _os.environ.get("TOOLGATE_API_KEY") or _secret_or_none("toolgate-api-key"),
            "TOOLGATE_BASE_URL": _os.environ.get("TOOLGATE_BASE_URL", "http://localhost:5050"),
            "TOOLGATE_AGENT_ID": _os.environ.get("TOOLGATE_AGENT_ID") or _secret_or_none("toolgate-agent-id"),
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
    "calendar": "The agent's own internal calendar (SQLite-backed). Add single-day or multi-day events (e.g. trips) with a title, time frame, location, and notes; read a day, a week, or a date range; update or delete events. Setting a reminder ties into the scheduler so you get pinged before an event.",
    "scheduler": "Create and manage recurring scheduled tasks (cron-like jobs, daily reminders).",
    "code": "Delegate coding tasks to Claude Code — research codebases, write/edit code, and manage background processes (start/stop dev servers, etc.).",
    "system": "Delegate system administration of the user's Mac to a careful, gated Claude Code admin — inspect and manage files, processes, services, installs, disk, network, logs, and configuration. Runs read-mostly: it investigates freely but stops and asks for the user's explicit approval before any change (then you resume it with approve=true). Use for anything about the state of the machine itself.",
    "claude_hub": "Observe and control your Claude Code sessions via Claude Hub — list projects/sessions, check which need attention, rename/flag them, and resume or start sessions in a terminal.",
    "imessage": "Read iMessage history — get recent messages, search conversations, check unread messages.",
    "fetch": "Fetch a URL and extract its contents as markdown. Read web pages, articles, and documentation.",
    "music": "Control Apple Music — play songs/artists/playlists, pause, skip, search library, get now playing, set volume.",
    "lights": "Control smart lights (Hue + Cync) — turn on/off, set brightness, change colors, activate scenes, control rooms. Light IDs are prefixed (hue:X, cync:X).",
    "tv": "Control the Samsung TV — power on/off (power-on takes ~5-20s via Wake-on-LAN), launch apps (Netflix, YouTube...), send remote key presses, switch inputs, set volume, open a URL in the TV browser. Launching an app/URL/input auto-wakes the TV if it's off — no need to power on first.",
    "windows": "Open Mac apps and arrange their windows across displays — launch an app onto a specific screen in a specific spot (halves, quarters, thirds, full, or exact fractions), move windows that are already open, list connected displays, and see the current window layout.",
    "dashboards": "Create, update, list, delete, and restore mini-dashboards. Uses Claude Code to build interactive web apps served at /d/<slug>/.",
    "workflows": "Author, inspect, and run named workflows — reusable multi-step routines built from tool calls, isolated LLM steps, and other workflows. create_workflow takes a JSON definition (name, description, params, steps, output); run_workflow runs one and returns only its final output. Each step's LLM calls run in their own context, so nothing pollutes this conversation.",
    "triggers": "Create and manage event triggers — automations that fire when something happens rather than on a schedule. Webhooks (iOS Shortcuts on the user's iPhone, other devices/services POSTing over Tailscale) and pollers (watch a URL or tool output for changes). Each trigger runs a workflow or an agent prompt and delivers the result to voice/telegram. create_trigger mints the webhook URL + secret; get_trigger_firings shows what fired and why.",
    "projects": "Track projects, tasks, and notes (the source of truth) and read project docs. get_project_context bundles everything about a project — record, tasks, notes, docs, GitHub issues/PRs/commits, and recent Claude Code sessions — in one call. Can also push a task to GitHub as an issue.",
    "composio": "Act on external apps (GitHub, Gmail, Slack, and 1000+ others) via Composio. Search the tool catalog for an action (results show each tool's required args), inspect a tool's exact arguments, run it by slug, connect an app account via OAuth, and list connected accounts.",
}

# These servers' tools are ALWAYS sent without needing activation.
# Memory tools must always be available so the agent can store facts anytime.
# lights/music/tv/calendar are the bread-and-butter voice commands: keeping them
# always-on saves a whole activate_skill LLM round on the first use after every
# restart or history clear — the single biggest voice-latency lever. Their
# schemas are small, so the per-turn token cost is trivial next to that round.
# (toolgate removed 2026-06-23 — disabled in favor of the activatable "composio" skill.)
ALWAYS_INCLUDE_SERVERS = ["memory", "lights", "music", "tv", "calendar"]

# Maximum tool-call rounds per user message (safety limit to prevent infinite loops)
MAX_TOOL_ROUNDS = 25

# =============================================================================
# AGENT CORE MODE  ("classic" | "flat")
# =============================================================================
# "classic": the default brain — skill-gated tools, injected memories/procedures,
#            fast-path intent router, threads, rolling summary, truncated results.
# "flat":    an experimental, simpler brain (see agent/flat_core.py) — exposes ALL
#            tools at once, injects NO memories or procedures, and keeps the FULL
#            transcript (every tool call + result) in the context window across
#            turns. Meant for a large-context model. Flip it live from the
#            dashboard config editor (reload_overrides picks it up per message) or
#            with AGENT_CORE_MODE=flat in the environment.
AGENT_CORE_MODE = _os.environ.get("AGENT_CORE_MODE", "classic")

# Flat core keeps its running transcript here, isolated from the classic
# conversation buffer so flipping modes never corrupts either one.
FLAT_SESSION_FILE = _os.path.join(APP_DIR, "memory", "data", "flat_session.json")

# Flat core knobs. Rounds can run higher than classic since the model does more
# in one context; the result cap is a very high finite guard (not truncation in
# practice) so a single pathological megabyte result can't blow the window.
FLAT_MAX_TOOL_ROUNDS = int(_os.environ.get("FLAT_MAX_TOOL_ROUNDS", "40"))
FLAT_MAX_TOOL_RESULT_CHARS = int(_os.environ.get("FLAT_MAX_TOOL_RESULT_CHARS", "200000"))

# Optional distinct model for the flat core (typically a larger-context one).
# Empty = use the same MODEL as classic.
FLAT_MODEL = _os.environ.get("FLAT_MODEL", "") or MODEL

# Telegram user ID for scheduled task notifications
TELEGRAM_NOTIFY_USER_ID = 6080568335

# =============================================================================
# VOICE (async hand-off)
# =============================================================================
# A voice turn answers synchronously if agent.process() finishes within this many
# seconds (quick commands — lights, time, simple questions — behave exactly as
# before). If it runs longer (e.g. it delegated to the code/system_admin tools,
# which drive headless Claude Code for minutes), the brain returns a short spoken
# ack now and pushes the real result to the voice service when it's done — so the
# voice request is never blocked on a multi-minute task. Live-tunable via overrides.
VOICE_RESPONSE_DEADLINE = float(_os.environ.get("VOICE_RESPONSE_DEADLINE", "20"))
# Where the standalone voice service listens for those pushed results.
VOICE_CALLBACK_URL = _os.environ.get("VOICE_CALLBACK_URL", "http://127.0.0.1:5002/speak")
# Wake-word-equivalent activation (watch gesture remote's voice_activate).
VOICE_WAKE_URL = _os.environ.get("VOICE_WAKE_URL", "http://127.0.0.1:5002/wake")

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
# GIT SYNC
# =============================================================================
# Polling service (launchd) that fetches + fast-forwards tracked projects' clones.
GIT_SYNC_ENABLED = True
GIT_SYNC_INTERVAL_SECONDS = 600      # informational; the launchd StartInterval owns the schedule
GIT_SYNC_FETCH_TIMEOUT = 120         # seconds per git fetch/merge
GIT_SYNC_REINDEX_ON_CHANGE = True    # reindex a project's search index after a successful pull

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
