"""
Entry point for the Canadian Household Financial Data Telegram Bot.

Usage:
    python main.py

Environment variables required (see .env.example):
    BOT_TOKEN           — Telegram Bot API token
    ANTHROPIC_API_KEY   — Anthropic Claude API key

Optional:
    LOG_LEVEL           — Logging level (default: INFO)
    POLL_ON_STARTUP     — Set to "true" to run an immediate poll at startup
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import Application, CommandHandler

# Load environment variables from .env file (dev convenience)
load_dotenv()

# --------------------------------------------------------------------------- #
#  Logging  (stdout only — Railway/Docker captures this natively)             #
# --------------------------------------------------------------------------- #

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.INFO)
logging.getLogger("feedparser").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Validation                                                                  #
# --------------------------------------------------------------------------- #

def _validate_env() -> None:
    missing = [k for k in ("BOT_TOKEN", "ANTHROPIC_API_KEY") if not os.environ.get(k)]
    if missing:
        logger.critical(
            "Missing required environment variables: %s\n"
            "Copy .env.example to .env and fill in the values.",
            ", ".join(missing),
        )
        sys.exit(1)


# --------------------------------------------------------------------------- #
#  Bot setup                                                                   #
# --------------------------------------------------------------------------- #

async def post_init(application: Application) -> None:
    """Run after the bot is initialised but before polling starts."""
    # Register bot commands in Telegram's UI
    await application.bot.set_my_commands([
        BotCommand("start",   "Welcome message & overview"),
        BotCommand("latest",  "Show 5 most recent updates"),
        BotCommand("search",  "Search updates by keyword"),
        BotCommand("filter",  "Filter updates by topic tag"),
        BotCommand("sources", "List all monitored sources"),
        BotCommand("digest",  "Generate weekly summary digest"),
    ])
    logger.info("Bot commands registered with Telegram")


async def run_startup_poll(application: Application) -> None:
    """Optionally run an immediate feed poll at startup."""
    if os.environ.get("POLL_ON_STARTUP", "").lower() == "true":
        logger.info("POLL_ON_STARTUP=true — running initial feed poll")
        from bot.scheduler import poll_feeds_job
        await poll_feeds_job(application)


def main() -> None:
    _validate_env()
    logger.info("Starting Canadian Household Financial Data Bot")

    # Ensure data directory exists (for SQLite DB); volume is mounted by now
    import pathlib
    pathlib.Path("data").mkdir(exist_ok=True)

    # Initialise database
    from bot.database import init_db
    init_db()

    # Import command handlers
    from bot.commands import (
        digest_command,
        error_handler,
        filter_command,
        latest_command,
        search_command,
        sources_command,
        start_command,
    )

    # Build the Telegram application
    token = os.environ["BOT_TOKEN"]
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start",   start_command))
    application.add_handler(CommandHandler("latest",  latest_command))
    application.add_handler(CommandHandler("search",  search_command))
    application.add_handler(CommandHandler("sources", sources_command))
    application.add_handler(CommandHandler("digest",  digest_command))
    application.add_handler(CommandHandler("filter",  filter_command))
    application.add_error_handler(error_handler)

    # Set up scheduler
    from bot.scheduler import setup_scheduler
    scheduler = setup_scheduler(application)

    async def _run() -> None:
        async with application:
            scheduler.start()
            logger.info(
                "Scheduler started. Next feed poll: %s",
                scheduler.get_job("poll_feeds").next_run_time,
            )
            await run_startup_poll(application)
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            logger.info("Bot is running. Press Ctrl+C to stop.")
            # Keep running until interrupted
            try:
                await asyncio.Event().wait()
            except (KeyboardInterrupt, SystemExit):
                pass
            finally:
                logger.info("Shutting down…")
                scheduler.shutdown(wait=False)
                await application.updater.stop()
                await application.stop()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


if __name__ == "__main__":
    main()
