"""
Telegram bot command handlers.

All handlers are async functions compatible with python-telegram-bot v20+.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.database import (
    filter_by_tag,
    get_all_chats,
    get_latest_updates,
    get_weekly_updates,
    register_chat,
    search_updates,
)
from bot.formatter import (
    format_digest,
    format_filter_results,
    format_latest,
    format_search_results,
    format_sources_list,
    format_update_from_row,
    format_welcome,
)
from bot.summarizer import generate_weekly_digest

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Helpers                                                                     #
# --------------------------------------------------------------------------- #

async def _send_html(update: Update, text: str) -> None:
    """Send a single HTML-formatted message, logging errors."""
    try:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.error("Failed to send message: %s", exc)


async def _send_html_list(update: Update, messages: list) -> None:
    """Send a list of HTML messages sequentially."""
    for msg in messages:
        await _send_html(update, msg)


# --------------------------------------------------------------------------- #
#  Broadcast helper (used by scheduler)                                        #
# --------------------------------------------------------------------------- #

async def broadcast_update(context: ContextTypes.DEFAULT_TYPE, update_dict: dict) -> None:
    """Send a formatted update to all registered chat IDs."""
    from bot.formatter import format_update
    text = format_update(update_dict)
    chats = get_all_chats()
    for chat_id in chats:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logger.warning("Could not send to chat %s: %s", chat_id, exc)


async def broadcast_digest(context: ContextTypes.DEFAULT_TYPE, digest_text: str) -> None:
    """Send the weekly digest to all registered chat IDs."""
    messages = format_digest(digest_text)
    chats = get_all_chats()
    for chat_id in chats:
        for msg in messages:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception as exc:
                logger.warning("Could not send digest to chat %s: %s", chat_id, exc)


# --------------------------------------------------------------------------- #
#  Command handlers                                                            #
# --------------------------------------------------------------------------- #

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — Welcome message and register the chat for broadcasts."""
    chat_id = update.effective_chat.id
    register_chat(chat_id)
    logger.info("New chat registered: %s", chat_id)
    await _send_html(update, format_welcome())


async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/latest — Show the 5 most recent updates."""
    rows = get_latest_updates(limit=5)
    messages = format_latest(rows)
    await _send_html_list(update, messages)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/search [keyword] — Search cached updates by topic."""
    if not context.args:
        await _send_html(
            update,
            "🔍 Usage: <code>/search [keyword]</code>\n\nExample: <code>/search mortgage</code>",
        )
        return

    keyword = " ".join(context.args).strip()
    if len(keyword) < 2:
        await _send_html(update, "⚠️ Please provide at least 2 characters to search.")
        return

    rows = search_updates(keyword, limit=5)
    messages = format_search_results(rows, keyword)
    await _send_html_list(update, messages)


async def sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/sources — List all monitored sources."""
    await _send_html(update, format_sources_list())


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/digest — Generate and send a weekly summary digest on demand."""
    await _send_html(update, "⏳ Generating your weekly digest with Claude AI… this may take 15–30 seconds.")

    updates = get_weekly_updates()
    update_dicts = [dict(row) for row in updates]

    digest_text = await generate_weekly_digest(update_dicts)

    if not digest_text:
        await _send_html(
            update,
            "❌ Could not generate digest right now. Please try again later.",
        )
        return

    messages = format_digest(digest_text)
    await _send_html_list(update, messages)


async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/filter [tag] — Filter updates by topic tag (e.g. /filter #debt)."""
    if not context.args:
        await _send_html(
            update,
            "🏷️ Usage: <code>/filter [tag]</code>\n\n"
            "Available tags:\n"
            "<code>#debt #housing #savings #inflation #income #credit "
            "#sentiment #tax #retirement #banking #generational #investment</code>\n\n"
            "Example: <code>/filter #housing</code>",
        )
        return

    tag = context.args[0].strip().lower()
    if not tag.startswith("#"):
        tag = f"#{tag}"

    rows = filter_by_tag(tag, limit=5)
    messages = format_filter_results(rows, tag)
    await _send_html_list(update, messages)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error("Exception while handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "❌ An unexpected error occurred. Please try again.",
        )
