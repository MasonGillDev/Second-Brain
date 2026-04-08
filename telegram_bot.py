"""
Second Brain - Telegram interface.

Connects the same agent brain (memory, tools, LLM) to Telegram.
Run alongside or instead of the CLI.

Usage:
    python telegram_bot.py
"""

import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import config
from core import AgentCore

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

# Shared agent instance
agent: AgentCore | None = None

# Optional: restrict to your Telegram user ID for security.
# Find yours by messaging @userinfobot on Telegram.
# Set to None to allow anyone (not recommended).
ALLOWED_USER_IDS: set[int] | None = {6080568335}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "🧠 Second Brain is online.\n\n"
        "Just send me a message and I'll respond with full memory and tool access.\n\n"
        "Commands:\n"
        "/remember <text> — Store in long-term memory\n"
        "/stats — Memory statistics\n"
        "/clear — Clear conversation history"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command."""
    agent.memory.conversation.clear_session()
    await update.message.reply_text("Conversation cleared. Long-term memories preserved.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages."""
    if not update.message or not update.message.text:
        return

    # Security: check user ID if allowlist is set
    if ALLOWED_USER_IDS and update.message.from_user.id not in ALLOWED_USER_IDS:
        await update.message.reply_text("Unauthorized.")
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    # Show "typing..." indicator
    await update.message.chat.send_action("typing")

    try:
        response = await agent.process(user_text)

        # Telegram has a 4096 char limit per message
        if len(response) <= 4096:
            await update.message.reply_text(response)
        else:
            # Split into chunks
            for i in range(0, len(response), 4096):
                await update.message.reply_text(response[i:i + 4096])

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def post_init(application: Application):
    """Called after the bot app is initialized — start the agent."""
    global agent
    agent = AgentCore()
    print("  Starting agent core...")
    await agent.start()

    stats = agent.memory.vector_store.get_stats()
    non_empty = {k: v for k, v in stats.items() if v > 0}
    if non_empty:
        print(f"  Loaded memories: {non_empty}")
    print("  Telegram bot is running. Send a message to your bot.")


async def post_shutdown(application: Application):
    """Called on shutdown — clean up the agent."""
    if agent:
        print("\n  Shutting down agent...")
        await agent.shutdown()
        print("  Goodbye!")


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║        🧠 Second Brain — Telegram Bot           ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # /remember and /stats are handled by AgentCore.process() via the text handler
    # but Telegram treats /remember as a command, so we need a handler for it
    async def remember_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text  # includes "/remember"
        await update.message.chat.send_action("typing")
        response = await agent.process(text)
        await update.message.reply_text(response)

    async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        response = await agent.process("/stats")
        await update.message.reply_text(response)

    app.add_handler(CommandHandler("remember", remember_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # Run the bot
    app.run_polling()


if __name__ == "__main__":
    main()
