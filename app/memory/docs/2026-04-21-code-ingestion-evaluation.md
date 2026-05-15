# Code Ingestion System — Evaluation Report

**Date:** 2026-04-21
**Project indexed:** Benson (Slyd-Platform) — .NET 8 / Blazor, ~380 source files

---

## Overview

We built a code ingestion pipeline that extracts documentation-level context (XML doc comments, block comments, class declarations) from codebases and stores them as vector embeddings in ChromaDB. The goal: give the Second Brain agent instant architectural knowledge without expensive file-by-file exploration.

This document captures our findings from testing it against the Benson codebase.

---

## Ingestion Pipeline

### What gets extracted
- **C# XML doc comments** (`/// <summary>`, `<param>`, `<returns>`, `<remarks>`) paired with their declarations
- **Block comments** (`/* */`, `/** */`) with associated declaration context
- **Comment blocks** (consecutive `//` lines grouped together)
- **Class/interface/struct/enum/record declarations** (even without comments — these are high-value type definitions)
- **Razor-specific:** `@page` routes, `@inject` directives, `@code {}` blocks, `@* *@` comments, `<!-- -->` comments

### What gets filtered out
- Bare namespace declarations
- Bare method/property signatures with no documentation
- Files matching `.gitignore` patterns (via `git check-ignore`)
- Directories: `bin/`, `obj/`, `.vs/`, `Migrations/`, `wwwroot/`, `node_modules/`, etc.
- Files exceeding 100KB

### Chunk reduction
| Pass | Chunks | Notes |
|------|--------|-------|
| Initial (all signatures + comments) | 7,863 | Every method, property, namespace extracted |
| After filtering bare signatures | 1,328 | 83% reduction, only documented code + type declarations |

The 1,328-chunk version significantly outperformed the 7,863-chunk version in retrieval quality. The larger set returned noise (namespace declarations, trivial property signatures) that drowned out meaningful results.

---

## Retrieval Configuration

| Setting | Initial | Final |
|---------|---------|-------|
| `RETRIEVAL_TOP_K_CODE` | 3 | 12 |
| `RETRIEVAL_MIN_RELEVANCE_CODE` | 0.38 | 0.30 |

The initial settings were too restrictive — only 3 results meant the agent couldn't synthesize answers spanning multiple services. 12 results with a 0.30 threshold gives enough coverage for cross-cutting architectural questions.

---

## Test Results

We tested five architectural prompts and compared three response tiers:

1. **Second Brain only** — vector retrieval, no file reads
2. **Second Brain + code review tool** — retrieval informs targeted file exploration
3. **Claude Code** — full codebase exploration from scratch (control)

### Test 1: Payment Services Architecture
| Tier | Quality | Key findings |
|------|---------|--------------|
| SB only (v1, 7863 chunks) | Poor | Returned 12 `namespace Benson.Infrastructure.Services.Payments;` lines — zero useful content |
| SB only (v2, 1328 chunks) | Good | Identified service names, roles, and relationships correctly |
| Claude Code | Excellent | Found 10+ specific services with implementation details |

**Takeaway:** Chunk quality matters more than quantity. Fewer, meaningful chunks dramatically improved results.

### Test 2: Real-Time Chat Streaming
| Tier | Quality | Key findings |
|------|---------|--------------|
| SB only | Good | Found `ChatStreamChunk`, `EventBusService`, `ConsoleCommandService`, described the streaming flow |
| Claude Code | Excellent | Also found SignalR hub details and specific streaming patterns |

**Takeaway:** Architectural flow questions are the sweet spot for ingestion.

### Test 3: MCP Tool Organization
| Tier | Quality | Key findings |
|------|---------|--------------|
| SB only | Moderate | Got categories, routing architecture, `ToolModeMatrix` permission system |
| SB + code review | Good | More specific tool names and delivery modes |
| Claude Code | Excellent | Enumerated all 162 tools across 14 categories |

**Takeaway:** Enumeration questions ("list all X") are a weakness. The ingestion captures documentation *about* code, not exhaustive inventories.

### Test 4: Agent Spawning & Privilege Escalation Prevention
| Tier | Quality | Key findings |
|------|---------|--------------|
| SB only | Good | Dual identity system, parent-child auth, role-based restrictions, ~70% of full answer |
| SB + code review | Very Good | Added specific dollar limits, tool intersection logic, delegation depth |
| Claude Code | Excellent | No-wallet design as escalation prevention, 6-layer gating model, spawn rollback semantics |

**Takeaway:** Security architecture questions work well because security decisions are typically documented in comments.

### Test 5: Multi-Step Workflows & Failure Handling
| Tier | Quality | Key findings |
|------|---------|--------------|
| SB only | Moderate | Found `WorkflowResult` DTO, described partial completion — but **incorrectly inferred** workflows continue after failure (they actually fail-fast) |
| SB + code review | Good | Corrected to fail-fast, found specific workflow steps, retry logic |
| Claude Code | Excellent | Four distinct execution layers, loop detection thresholds, complete failure recovery matrix |

**Takeaway:** Documentation-level understanding can mislead. A DTO showing `StepsFailed > 0` implied continuation, but the implementation does fail-fast. This is the risk of summaries without implementation verification.

---

## Strength / Weakness Summary

### Strengths (use ingestion alone)
- "How does X work?" — architectural overviews
- "What's the relationship between X and Y?" — cross-service understanding
- "What components handle X?" — service discovery
- Security/authorization architecture (well-documented in comments)
- Giving the code review tool a targeted starting point

### Weaknesses (need file reads)
- "List every X" — enumeration requires reading registration code
- "What are the exact validation rules?" — inline logic, guard clauses
- "What happens in edge case Y?" — error handling paths
- Anything where the comments/docs don't match the implementation

### The Compound Effect
The most important finding: **even when the ingestion can't fully answer a question, it makes the code review tool dramatically more efficient.** Instead of 29 tool calls and 88k tokens exploring blind, the agent gets a map first and does targeted reads. The ingestion serves as a knowledge layer that accelerates everything downstream.

---

## Architecture Diagram

```
User Query
    │
    ▼
┌─────────────────────┐
│  Vector Search       │  ← 1,328 chunks in code_context
│  (ChromaDB)          │     12 results, 0.30 min relevance
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Sufficient?         │──▶  │  Return answer       │
│  (agent decides)     │ yes │  (instant, ~0 tokens) │
└─────────┬───────────┘     └─────────────────────┘
          │ no
          ▼
┌─────────────────────┐
│  Code Review Tool    │  ← Targeted reads informed by
│  (file reads)        │     retrieved context
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Return answer       │  ← Faster than cold-start
│  (moderate cost)     │     exploration
└─────────────────────┘
```

---

## Cost Comparison

| Approach | Tokens | Time | Quality |
|----------|--------|------|---------|
| Second Brain only | ~0 | instant | 70-85% |
| Second Brain + code review | moderate | ~15s | 85-95% |
| Claude Code (no ingestion) | 88k+ | 1+ min | 95-100% |

The ingestion pays for itself after a handful of queries. The indexing cost is one-time (re-run only when code changes significantly), and every subsequent query saves the full exploration cost.
