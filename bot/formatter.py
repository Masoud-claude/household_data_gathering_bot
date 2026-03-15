"""
Telegram message formatter.

Produces HTML-formatted messages for each update and digest.
All text sent through python-telegram-bot must be safe for Telegram's
HTML parse mode (we escape user-generated text where needed).
"""

import html
from datetime import datetime, timezone
from typing import List, Optional

from bot.sources import CATEGORY_TAGS


# Maximum length Telegram allows per message
TELEGRAM_MAX_CHARS = 4096
DIGEST_CHUNK_SIZE = 3800   # leave headroom for split labels


def _escape(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse_mode."""
    return html.escape(text, quote=False)


def _format_date(iso_date: Optional[str]) -> str:
    if not iso_date:
        return "Unknown date"
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except Exception:
        return iso_date


def format_update(update: dict) -> str:
    """
    Format a single update dict as a Telegram HTML message.

    Expected keys: title, source_name, category, published, summary, url, tags
    """
    source_name = _escape(update.get("source_name", "Unknown Source"))
    category = update.get("category", "")
    category_label = CATEGORY_TAGS.get(category, category)
    title = _escape(update.get("title", "Untitled"))
    published = _format_date(update.get("published"))
    url = update.get("url", "#")
    tags = update.get("tags", "")
    summary = update.get("summary") or "_No summary available_"

    # Build bullet points — summary lines start with "•"
    bullet_lines = []
    for line in summary.splitlines():
        line = line.strip()
        if line:
            if not line.startswith("•"):
                line = f"• {line}"
            bullet_lines.append(_escape(line))

    bullets_text = "\n".join(bullet_lines) if bullet_lines else "• No summary available"

    tag_line = " ".join(
        f"<code>{_escape(t)}</code>" for t in tags.split() if t.startswith("#")
    )

    msg = (
        f"📌 <b>{source_name}</b>  <i>{category_label}</i>\n\n"
        f"📰 <b>{title}</b>\n\n"
        f"🗓️ {published}\n\n"
        f"🔑 <b>Key Findings:</b>\n{bullets_text}\n\n"
        f"🔗 <a href=\"{url}\">Read the full report</a>\n\n"
        f"🏷️ {tag_line}"
    )

    # Trim to Telegram limit if somehow too long
    if len(msg) > TELEGRAM_MAX_CHARS:
        msg = msg[: TELEGRAM_MAX_CHARS - 3] + "..."

    return msg


def format_update_from_row(row) -> str:
    """Convenience wrapper accepting a sqlite3.Row."""
    return format_update(dict(row))


def format_latest(updates: List) -> List[str]:
    """
    Format the /latest command response.
    Returns a list of message strings (one per update).
    """
    if not updates:
        return ["📭 No updates found yet. The bot will start collecting data on its next scheduled poll."]
    return [format_update_from_row(u) for u in updates]


def format_search_results(updates: List, keyword: str) -> List[str]:
    if not updates:
        return [f"🔍 No results found for <b>{_escape(keyword)}</b>."]
    header = f"🔍 Search results for <b>{_escape(keyword)}</b> ({len(updates)} found):\n\n"
    messages = [header] + [format_update_from_row(u) for u in updates]
    return messages


def format_filter_results(updates: List, tag: str) -> List[str]:
    if not updates:
        return [f"🏷️ No updates found for tag <b>{_escape(tag)}</b>."]
    header = f"🏷️ Updates tagged <b>{_escape(tag)}</b> ({len(updates)} found):\n\n"
    messages = [header] + [format_update_from_row(u) for u in updates]
    return messages


def format_sources_list() -> str:
    """Format the /sources command response."""
    from bot.sources import SOURCES

    gov_sources = [s for s in SOURCES if s.category == "Government"]
    research_sources = [s for s in SOURCES if s.category == "Research"]
    media_sources = [s for s in SOURCES if s.category == "Media"]

    def _list(sources) -> str:
        return "\n".join(f"  • <a href=\"{s.url}\">{_escape(s.name)}</a>" for s in sources)

    return (
        "📡 <b>Monitored Sources</b>\n\n"
        f"🏛️ <b>Government & Regulatory ({len(gov_sources)})</b>\n{_list(gov_sources)}\n\n"
        f"🔬 <b>Research & Non-Governmental ({len(research_sources)})</b>\n{_list(research_sources)}\n\n"
        f"📰 <b>Media & Aggregators ({len(media_sources)})</b>\n{_list(media_sources)}\n\n"
        f"<i>Feeds polled every 6 hours. New Canadian household financial data delivered automatically.</i>"
    )


def format_welcome() -> str:
    """Format the /start command welcome message."""
    return (
        "🇨🇦 <b>Canadian Household Financial Data Bot</b>\n\n"
        "Welcome! I monitor <b>20+ trusted Canadian sources</b> — government, "
        "research institutions, and media — and deliver curated updates on:\n\n"
        "💸 Household debt &amp; credit trends\n"
        "🏡 Housing affordability &amp; mortgage stress\n"
        "💰 Savings rates, TFSA/RRSP/FHSA data\n"
        "📊 Consumer confidence &amp; sentiment surveys\n"
        "🧾 Income inequality &amp; wage growth\n"
        "🏦 Banking &amp; fintech adoption\n"
        "🧓 Retirement readiness &amp; pension data\n"
        "📱 Financial literacy &amp; mental health links\n\n"
        "<b>Commands:</b>\n"
        "/latest — 5 most recent updates\n"
        "/search [keyword] — search by topic\n"
        "/filter [tag] — filter by tag (e.g. <code>#debt</code>)\n"
        "/sources — all monitored sources\n"
        "/digest — weekly summary on demand\n\n"
        "<b>Available tags:</b>\n"
        "<code>#debt #housing #savings #inflation #income #credit "
        "#sentiment #tax #retirement #banking #generational #investment</code>\n\n"
        "⏰ <i>Feeds checked every 6 hours. Weekly digest auto-sent every Monday morning.</i>"
    )


def chunk_text(text: str, chunk_size: int = DIGEST_CHUNK_SIZE) -> List[str]:
    """Split long text into Telegram-safe chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    while text:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        # Find last newline before limit
        cut = text.rfind("\n", 0, chunk_size)
        if cut == -1:
            cut = chunk_size
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")

    return [f"{c}\n\n<i>(Part {i}/{len(chunks)})</i>" if len(chunks) > 1 else c
            for i, c in enumerate(chunks, 1)]


def format_digest(digest_text: str) -> List[str]:
    """Format and chunk the weekly digest for sending."""
    header = "📋 <b>Weekly Canadian Household Finance Digest</b>\n\n"
    full = header + _escape(digest_text)
    return chunk_text(full)
