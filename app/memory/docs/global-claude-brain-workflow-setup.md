# Global Claude Brain / Documentation Workflow Setup

**Project:** Claude Code Configuration
**Date:** 2026-07-14
**Author:** a71428d6-3667-4dc4-a155-a8398ca7269c

## What Was Done

Created a global `~/.claude/CLAUDE.md` that instructs Claude to automatically document completed tasks and maintain a chronological timeline. The system has two components:

**Docs (`/Users/masongill/Brain/Docs/`):** One file per task. Each file captures what was done, what decisions were made and why, and any follow-up work. Written for future-you — context and reasoning, not just a list of changes.

**Timeline (`/Users/masongill/Brain/timeline.md`):** A prepend-only log. Each entry links to its doc, has a timestamp, session ID, and a status of either `Done` or `Follow-up Work` (derived from whether the doc has a "To Do Next" section).

The session ID used as author is the UUID from the scratchpad path Claude Code provides each session, which matches the ID used by `claude --resume`.

Also initialized `timeline.md` with an empty header so it's ready to receive entries.
