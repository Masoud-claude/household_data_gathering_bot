"""
APScheduler setup for periodic feed polling and weekly digest delivery.

Jobs:
  1. poll_feeds_job     — every 6 hours, polls all RSS sources and broadcasts
                          new items to registered chats
  2. weekly_digest_job  — every Monday at 08:00 ET, generates and broadcasts
                          the weekly digest
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram.ext import Application

from bot.database import get_all_chats, get_weekly_updates, mark_sent
from bot.monitor import poll_all_sources
from bot.summarizer import generate_weekly_digest

logger = logging.getLogger(__name__)


async def poll_feeds_job(application: Application) -> None:
    """
    Poll all configured RSS sources for new content.
    Broadcast each new item to all registered chats.
    """
    logger.info("Scheduled job: poll_feeds_job starting")
    try:
        new_items = await poll_all_sources()
        if not new_items:
            logger.info("poll_feeds_job: no new items found")
            return

        chats = get_all_chats()
        if not chats:
            logger.info("No registered chats — skipping broadcast")
            # Still mark as sent to avoid re-broadcasting when a chat eventually joins
            for item in new_items:
                mark_sent(item["url"])
            return

        from bot.commands import broadcast_update
        for item in new_items:
            await broadcast_update(application, item)
            mark_sent(item["url"])

        logger.info("poll_feeds_job: broadcast %d new items to %d chats", len(new_items), len(chats))

    except Exception as exc:
        logger.error("poll_feeds_job failed: %s", exc, exc_info=True)


async def weekly_digest_job(application: Application) -> None:
    """
    Generate and broadcast the weekly digest every Monday morning.
    """
    logger.info("Scheduled job: weekly_digest_job starting")
    try:
        updates = get_weekly_updates()
        if not updates:
            logger.info("weekly_digest_job: no updates in the past 7 days")
            return

        update_dicts = [dict(row) for row in updates]
        digest_text = await generate_weekly_digest(update_dicts)

        if not digest_text:
            logger.warning("weekly_digest_job: digest generation returned None")
            return

        from bot.commands import broadcast_digest
        await broadcast_digest(application, digest_text)
        logger.info("weekly_digest_job: digest broadcast complete")

    except Exception as exc:
        logger.error("weekly_digest_job failed: %s", exc, exc_info=True)


def setup_scheduler(application: Application) -> AsyncIOScheduler:
    """
    Create and configure the APScheduler instance.

    Returns a started AsyncIOScheduler.
    """
    scheduler = AsyncIOScheduler(timezone="America/Toronto")

    # Poll every 6 hours
    scheduler.add_job(
        poll_feeds_job,
        trigger=IntervalTrigger(hours=24),
        id="poll_feeds",
        name="Poll RSS Feeds",
        kwargs={"application": application},
        max_instances=1,
        coalesce=True,          # skip missed runs on restart
        misfire_grace_time=600, # 10 min grace period
    )

    # Weekly digest every Monday at 08:00 Eastern Time
    scheduler.add_job(
        weekly_digest_job,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="America/Toronto"),
        id="weekly_digest",
        name="Weekly Digest",
        kwargs={"application": application},
        max_instances=1,
        coalesce=True,
    )

    return scheduler
