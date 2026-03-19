"""
Feed monitoring module.

Polls RSS feeds from all configured sources, filters entries by relevance
keywords, deduplicates against the database, then summarises and stores
new items.
"""

import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional, Tuple

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bot.database import insert_update, url_exists
from bot.sources import GLOBAL_KEYWORDS, SOURCES, TOPIC_TAGS, Source
from bot.summarizer import summarise_article

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  HTTP session with retries                                          #
# ------------------------------------------------------------------ #

def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {"User-Agent": "CanadaFinBot/1.0 (+https://github.com/your-org/canada-fin-bot)"}
    )
    return session


SESSION = _make_session()


# ------------------------------------------------------------------ #
#  Relevance filtering                                                #
# ------------------------------------------------------------------ #

def _is_relevant(text: str, extra_keywords: List[str]) -> bool:
    """
    Return True if text contains at least one global or source-specific keyword.
    Case-insensitive matching.
    """
    lower = text.lower()
    all_kw = GLOBAL_KEYWORDS + extra_keywords
    return any(kw.lower() in lower for kw in all_kw)


def _extract_tags(text: str) -> str:
    """
    Return a space-separated string of matching topic hashtags.
    E.g. '#debt #housing'
    """
    lower = text.lower()
    matched = []
    for tag, keywords in TOPIC_TAGS.items():
        if any(kw.lower() in lower for kw in keywords):
            matched.append(tag)
    return " ".join(matched) if matched else ""


# ------------------------------------------------------------------ #
#  Date parsing                                                        #
# ------------------------------------------------------------------ #

def _parse_date(entry: feedparser.FeedParserDict) -> Optional[str]:
    """
    Try to extract a published date from a feed entry.
    Returns an ISO-8601 string or None.
    """
    for attr in ("published", "updated", "created"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass
    # feedparser also exposes struct_time
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                dt = datetime(*parsed[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
    return None


# ------------------------------------------------------------------ #
#  Feed fetching                                                       #
# ------------------------------------------------------------------ #

def _fetch_feed(feed_url: str) -> Optional[feedparser.FeedParserDict]:
    """Fetch and parse a single RSS/Atom feed URL."""
    try:
        resp = SESSION.get(feed_url, timeout=20)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except requests.RequestException as exc:
        logger.warning("Could not fetch feed %s: %s", feed_url, exc)
        return None


def _get_entry_content(entry: feedparser.FeedParserDict) -> str:
    """Return the best available text content for an entry."""
    for attr in ("summary", "content", "description"):
        val = getattr(entry, attr, None)
        if val:
            if isinstance(val, list):
                return val[0].get("value", "")
            return val
    return ""


# ------------------------------------------------------------------ #
#  Main polling function                                              #
# ------------------------------------------------------------------ #

async def poll_all_sources() -> List[dict]:
    """
    Poll every configured source feed.
    Returns a list of newly processed update dicts.
    """
    new_items: List[dict] = []

    for source in SOURCES:
        logger.info("Polling source: %s (%d feeds)", source.name, len(source.feeds))
        for feed_url in source.feeds:
            items = await _process_feed(source, feed_url)
            new_items.extend(items)
            # Be polite between requests
            time.sleep(1)

    logger.info("Poll complete. %d new items found.", len(new_items))
    return new_items


async def _process_feed(source: Source, feed_url: str) -> List[dict]:
    """Process a single feed URL for a source. Returns list of new items."""
    feed = _fetch_feed(feed_url)
    if feed is None or not feed.entries:
        return []

    new_items = []
    for entry in feed.entries:
        url = getattr(entry, "link", None)
        title = getattr(entry, "title", "")

        if not url or not title:
            continue

        # Skip already-seen URLs
        if url_exists(url):
            continue

        # Build combined text for relevance check
        content = _get_entry_content(entry)
        combined_text = f"{title} {content}"

        if not _is_relevant(combined_text, source.extra_keywords):
            logger.debug("Filtered out (not relevant): %s", title[:80])
            continue

        # Parse date
        published = _parse_date(entry)

        # Extract topic tags — skip articles that match no specific topic
        tags = _extract_tags(combined_text)
        if not tags:
            logger.debug("Filtered out (no topic match): %s", title[:80])
            continue

        # Summarise with Claude
        logger.info("Summarising: %s", title[:80])
        summary = await summarise_article(title, content or title, url, source.name)

        # Store in DB
        insert_update(
            url=url,
            title=title,
            source_name=source.name,
            category=source.category,
            published=published,
            summary=summary,
            tags=tags,
        )

        new_items.append(
            {
                "url": url,
                "title": title,
                "source_name": source.name,
                "category": source.category,
                "published": published,
                "summary": summary,
                "tags": tags,
            }
        )

    return new_items
