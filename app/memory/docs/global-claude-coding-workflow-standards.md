# Global CLAUDE.md — Coding Workflow Standards

**Project:** Claude Code global configuration
**Date:** 2026-07-30
**Author:** 8ed887bb-864d-4e00-b174-9e2b02df0f43
**Directory:** /Users/masongill

## What Was Done
Added a "Coding Workflow Standards" section to `~/.claude/CLAUDE.md` so Claude follows production-engineer practices across all codebases. The goal was reliability — reducing plausible-but-unverified work.

The section covers six workflows:
- **Before writing code:** read surrounding code and match conventions, search for existing utilities before writing new ones, never guess APIs (read actual signatures), state a plan for changes touching 3+ files.
- **Bug fixes:** reproduce before fixing (failing test where possible), fix root cause not symptom, confirm the repro passes afterward.
- **Making changes:** small verified increments, check all call sites when changing shared code, keep changes minimal (no drive-by refactoring).
- **Verification (non-negotiable):** build + run relevant tests after every task, narrowest tests first, run linters, never claim completion without verification, report actual failure output.
- **Before finishing:** remove debug artifacts, self-review via `git diff`, no commits unless asked.
- **When stuck:** re-diagnose from scratch after 2–3 failed attempts instead of iterating on the same guess; ask when ambiguity changes the implementation.

Key reasoning behind what was included/excluded:
- Verification was made the strictest section because unverified "done" claims are the most common AI reliability failure.
- Rules were kept short and imperative — long prose in CLAUDE.md gets diluted.
- Deliberately excluded: mandatory tests for all new code (too rigid for scripts/prototypes) and TDD-by-default (better as a per-project rule than global).
