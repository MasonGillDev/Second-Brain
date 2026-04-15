"""
Sleep Agent — Memory Consolidation System.

Inspired by how the brain reorganizes memories during sleep.
Runs as a standalone script on a schedule or manually.

Usage:
    python sleep_agent.py              # run normally
    python sleep_agent.py --dry-run    # log what it would do, no changes
    python sleep_agent.py --notify     # send summary to Telegram when done
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime

import anthropic
import config
from keychain import get_secret
from memory.vector_store import VectorStore
from memory.recursive_search import recursive_similarity_search
from memory.sleep_tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS


SYSTEM_PROMPT = """You are the Sleep Agent for Second Brain, a memory consolidation system inspired by how the human brain reorganizes memories during sleep.

You have been given a batch of memories — recent ones and their related neighbors found through recursive similarity search. Your job is to leave the memory store in a cleaner, more useful state than you found it.

## Your Goals (in priority order)
1. **Split bloated entries**: If a single memory contains multiple unrelated facts, split it into separate focused memories. Each memory should be one atomic, standalone fact.
2. **Merge duplicates**: If two memories say essentially the same thing, merge them into one that preserves all unique details.
3. **Resolve contradictions**: If two memories contradict each other, keep the more recent or more specific one, or merge them with the updated information.
4. **Improve clarity**: Rewrite vague or poorly worded memories to be concise, standalone facts that would be useful to retrieve.
5. **Reorganize tiers**: Move memories to the appropriate tier:
   - **active**: Facts needed in daily conversation (preferences, current projects, identity, active relationships)
   - **reference**: Useful but not frequently needed (completed project details, historical decisions, past events)
   - **archive**: Outdated or rarely relevant (old preferences that were superseded, completed one-off tasks, stale project info)
6. **Tag accurately**: Ensure memories have the right category for retrieval (user_fact, preference, decision, project_context).

## Rules
- Do NOT delete memories unless they are exact duplicates with no unique information.
- Do NOT invent new information. Only reorganize what exists.
- When merging, preserve the more specific or more recent version of conflicting details.
- When splitting, ensure every piece of information from the original is preserved in one of the new entries.
- When in doubt, leave a memory alone. Conservative action is better than data loss.
- Work through the memories systematically. You can make multiple tool calls per turn.
- Call `done` with a summary when you are finished.

## Memory Tiers
- **active** (collection: long_term): High-frequency recall. Core identity, current preferences, active projects, relationships.
- **reference** (collection: reference): Medium-frequency. Completed work, historical context, stable knowledge.
- **archive** (collection: archive): Low-frequency. Superseded facts, old context, rarely needed but not worth deleting.

## Read-Only Context
Memories with tier "documents" are ingested reference documents. You CANNOT modify them. Use them as context to inform your decisions about long-term memories — for example, if a document provides detail about a project, you can use that to improve or enrich a related long-term memory."""


def _setup_logging(log_dir: str) -> logging.Logger:
    """Configure file + console logging."""
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_file = os.path.join(log_dir, f"sleep_{timestamp}.log")

    logger = logging.getLogger("sleep_agent")
    logger.setLevel(logging.DEBUG)

    # File handler (detailed)
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-5s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))

    # Console handler (info only)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("  [sleep] %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def _format_batch(batch: list[dict]) -> str:
    """Format the memory batch for the LLM."""
    lines = [f"## Memory Batch ({len(batch)} memories)\n"]

    for mem in batch:
        meta = mem["metadata"] or {}
        created = datetime.fromtimestamp(meta.get("created_at", 0)).strftime("%Y-%m-%d") if meta.get("created_at") else "unknown"
        category = meta.get("category", meta.get("type", "general"))
        access = meta.get("access_count", 0)

        read_only = " ⚠ READ-ONLY" if mem["tier"] == "documents" else ""
        lines.append(f"[{mem['id']}] (tier: {mem['tier']}, relevance: {mem['effective_relevance']}, depth: {mem['depth']}){read_only}")
        lines.append(f"Category: {category} | Created: {created} | Accessed: {access}x")
        lines.append(f"Text: {mem['text']}")
        lines.append("---")

    return "\n".join(lines)


def _notify_telegram(summary: str):
    """Send summary to Telegram."""
    import requests
    from keychain import get_secret
    try:
        token = get_secret("telegram-bot-token")
    except RuntimeError:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": config.TELEGRAM_NOTIFY_USER_ID,
                "text": f"🧠 Sleep Agent Complete\n\n{summary}",
            },
            timeout=10,
        )
    except Exception:
        pass


def run_sleep_cycle(dry_run: bool = False, notify: bool = False):
    """Run one sleep consolidation cycle."""
    logger = _setup_logging(config.SLEEP_LOG_DIR)
    logger.info("Sleep cycle started" + (" (DRY RUN)" if dry_run else ""))

    # Initialize
    vs = VectorStore()
    client = anthropic.Anthropic(api_key=get_secret("anthropic-api-key"))

    # Count memories before
    counts_before = {
        "active": vs.collections["long_term"].count(),
        "reference": vs.collections["reference"].count(),
        "archive": vs.collections["archive"].count(),
    }
    logger.info(f"Memory counts before: {counts_before}")

    # Recursive search
    batch = recursive_similarity_search(vs)
    logger.info(f"Recursive search: {config.SLEEP_MAX_SEEDS} max seeds -> {len(batch)} unique memories (depth {config.SLEEP_SEARCH_DEPTH})")

    if not batch:
        logger.info("No memories to process. Exiting.")
        return

    # Log the batch
    for mem in batch:
        logger.debug(f"  [{mem['id']}] (tier:{mem['tier']} rel:{mem['effective_relevance']} d:{mem['depth']}) {mem['text'][:80]}")

    if dry_run:
        logger.info("DRY RUN — would send batch to agent. No changes made.")
        return

    # Build messages
    batch_text = _format_batch(batch)
    messages = [{"role": "user", "content": batch_text}]

    # Agent loop
    total_actions = 0
    action_log = []
    total_input_tokens = 0
    total_output_tokens = 0

    for round_num in range(config.SLEEP_MAX_TOOL_ROUNDS):
        try:
            response = client.messages.create(
                model=config.SLEEP_MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            break

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Parse response
        tool_calls = []
        text_parts = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if text_parts:
            logger.debug(f"[round {round_num + 1}] Agent: {' '.join(text_parts)[:200]}")

        if not tool_calls:
            break

        # Build assistant message for history
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute tools
        tool_results = []
        done_summary = None

        for tc in tool_calls:
            name = tc.name
            args = tc.input

            logger.debug(f"[round {round_num + 1}] {name}({json.dumps(args)[:150]})")

            if name == "done":
                done_summary = args.get("summary", "No summary provided.")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": "Done acknowledged.",
                })
                continue

            func = TOOL_FUNCTIONS.get(name)
            if not func:
                result = f"Unknown tool: {name}"
            else:
                try:
                    # All tool functions take vs as first arg
                    result = func(vs, **args)
                except Exception as e:
                    result = f"Error: {e}"
                    logger.warning(f"Tool error: {name} -> {e}")

            logger.debug(f"  -> {result[:150]}")
            action_log.append({"tool": name, "args": args, "result": result})
            total_actions += 1

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        if done_summary:
            logger.info(f"Agent summary: {done_summary}")
            break

        if round_num == config.SLEEP_MAX_TOOL_ROUNDS - 1:
            logger.warning(f"Hit max tool rounds ({config.SLEEP_MAX_TOOL_ROUNDS})")

    # Count memories after
    counts_after = {
        "active": vs.collections["long_term"].count(),
        "reference": vs.collections["reference"].count(),
        "archive": vs.collections["archive"].count(),
    }

    # Summarize
    cost = (total_input_tokens / 1000) * config.INPUT_COST_PER_1K + \
           (total_output_tokens / 1000) * config.OUTPUT_COST_PER_1K

    logger.info(f"Actions: {total_actions}")
    logger.info(f"Memories before: {counts_before} | after: {counts_after}")
    logger.info(f"Tokens: {total_input_tokens} in, {total_output_tokens} out | Est cost: ${cost:.4f}")
    logger.info("Sleep cycle complete")

    if notify:
        summary = (
            f"Actions: {total_actions}\n"
            f"Before: {counts_before}\n"
            f"After: {counts_after}\n"
            f"Cost: ${cost:.4f}"
        )
        if done_summary:
            summary = f"{done_summary}\n\n{summary}"
        _notify_telegram(summary)


def main():
    parser = argparse.ArgumentParser(description="Sleep Agent — Memory Consolidation")
    parser.add_argument("--dry-run", action="store_true", help="Log what would happen without making changes")
    parser.add_argument("--notify", action="store_true", help="Send summary to Telegram when done")
    args = parser.parse_args()

    if not config.SLEEP_AGENT_ENABLED:
        print("  [sleep] Disabled in config. Set SLEEP_AGENT_ENABLED = True to enable.")
        sys.exit(0)

    run_sleep_cycle(dry_run=args.dry_run, notify=args.notify)


if __name__ == "__main__":
    main()
