"""
Second Brain - CLI interface.

Commands:
  /remember <text>     - Store something in long-term memory
  /forget <text>       - Search and remove a memory
  /episode <summary> | <outcome>  - Store an episodic memory
  /procedure <name> | <description> | <steps>  - Store a procedural memory
  /ingest              - Re-scan and ingest docs from ./memory/docs/
  /stats               - Show memory statistics
  /summary             - Show the current rolling summary
  /clear               - Clear conversation history
  /tools               - List available tools
  /help                - Show available commands
  /quit                - Exit
"""

import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agent.core import AgentCore


def print_help():
    print("""
╔══════════════════════════════════════════════════╗
║            Second Brain - Commands               ║
╠══════════════════════════════════════════════════╣
║  /remember <text>    Store in long-term memory   ║
║  /forget <text>      Remove a memory             ║
║  /episode <s> | <o>  Store an episode            ║
║  /procedure <n>|<d>|<s>  Store a procedure       ║
║  /ingest             Ingest docs from ./memory/  ║
║  /stats              Memory statistics           ║
║  /memories           List all long-term memories ║
║  /summary            Show rolling summary        ║
║  /clear              Clear conversation history   ║
║  /tools              List available tools         ║
║  /help               Show this help              ║
║  /quit               Save & exit                 ║
╚══════════════════════════════════════════════════╝
    """)


def handle_local_command(command: str, agent: AgentCore) -> bool:
    """Handle CLI-only slash commands. Returns True if handled."""
    parts = command.strip().split(None, 1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/quit":
        return False  # Signal to exit

    elif cmd == "/help":
        print_help()

    elif cmd == "/forget":
        if not arg:
            print("  Usage: /forget <search text>")
            return True
        results = agent.memory.vector_store.query("long_term", arg, top_k=1)
        if results:
            agent.memory.vector_store.delete("long_term", results[0]["id"])
            print(f"  ✓ Removed: {results[0]['text'][:80]}...")
        else:
            print("  No matching memory found.")

    elif cmd == "/episode":
        if "|" not in arg:
            print("  Usage: /episode <summary> | <outcome>")
            return True
        parts = [p.strip() for p in arg.split("|", 1)]
        agent.memory.store_episode(parts[0], parts[1])
        print("  ✓ Episode stored.")

    elif cmd == "/procedure":
        if arg.count("|") < 2:
            print("  Usage: /procedure <name> | <description> | <steps>")
            return True
        parts = [p.strip() for p in arg.split("|", 2)]
        agent.memory.store_procedure(parts[0], parts[1], parts[2])
        print(f"  ✓ Procedure '{parts[0]}' stored.")

    elif cmd == "/ingest":
        count = agent.memory.ingest_docs()
        print(f"  ✓ Ingested {count} new chunks from ./memory/docs/")

    elif cmd == "/summary":
        summary = agent.memory.conversation.rolling_summary
        if summary:
            print(f"\n  Rolling Summary:\n{summary}\n")
        else:
            print("  No summary yet (conversation too short).")

    elif cmd == "/clear":
        agent.memory.conversation.clear_session()
        print("  ✓ Conversation cleared. Long-term memories are preserved.")

    elif cmd == "/tools":
        tools = agent.router.get_tools()
        if tools:
            print(f"\n  Available Tools ({len(tools)}):")
            for t in tools:
                print(f"  ├─ {t['name']}: {t['description'][:60]}")
            print()
        else:
            print("  No tools available.")

    else:
        return None  # Not a local command — pass to core

    return True


async def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║           🧠 Second Brain Agent                 ║")
    print("║     Type /help for commands, /quit to exit      ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    agent = AgentCore()
    if config.TOOLS_ENABLED:
        print("  Starting tool servers...")
    await agent.start()

    # Show initial stats
    stats = agent.memory.vector_store.get_stats()
    non_empty = {k: v for k, v in stats.items() if v > 0}
    if non_empty:
        print(f"  Loaded memories: {non_empty}")
    print()

    try:
        while True:
            try:
                user_input = await asyncio.to_thread(input, "You: ")
                user_input = user_input.strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if not user_input:
                continue

            # Handle CLI-only commands
            if user_input.startswith("/"):
                result = handle_local_command(user_input, agent)
                if result is False:  # /quit
                    break
                if result is True:  # Handled
                    continue
                # result is None — pass through to core (e.g., /remember, /stats)

            try:
                response = await agent.process(user_input)
                print(f"\nAgent: {response}\n")
            except Exception as e:
                print(f"\n  [error] {e}\n")

    finally:
        await agent.shutdown()
        print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
