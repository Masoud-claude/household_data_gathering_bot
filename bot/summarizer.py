"""
Summarisation module using the Anthropic Claude API.

Uses claude-sonnet-4-6 (cost-effective for high-volume summarisation) with
streaming to avoid request timeouts on long articles.
"""

import logging
import os
from typing import List, Optional

import anthropic

logger = logging.getLogger(__name__)

# Model tuned for cost-efficiency on high-volume summarisation tasks
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You are a senior financial analyst assistant helping a Canadian fintech startup \
founder stay informed about Canadian household and personal finance trends.

Your job is to read excerpts from reports, surveys, and news articles and \
produce concise, founder-relevant summaries. Always be:
- Neutral and factual
- Focused on data, statistics, and actionable insights
- Mindful of implications for fintech product development
- Brief (3–5 bullet points maximum)

Respond ONLY with bullet points. No preamble, no closing remarks."""

SUMMARY_PROMPT_TEMPLATE = """\
Source: {source_name}
Title: {title}
URL: {url}

Content:
{content}

---
Summarise the above in 3–5 bullet points. Each bullet must:
• Start with a specific data point or key finding (include % or $ figures if available)
• Be a single sentence
• Relate to Canadian households, consumers, or personal finances

Format: plain text bullet points starting with "•"
"""

DIGEST_SYSTEM_PROMPT = """\
You are an expert financial analyst for a Canadian fintech startup founder. \
You read weekly compilations of Canadian household financial data and produce \
a concise weekly digest with strategic founder insights."""

DIGEST_PROMPT_TEMPLATE = """\
Below are this week's top Canadian household and financial data updates.

{updates_text}

---
Write a weekly digest with two sections:

**1. Top Updates (5–7 most impactful):**
List each with:
• Title
• One-sentence key finding
• Why it matters for fintech

**2. Founder's Lens:**
In 3–5 bullet points, highlight the single most important strategic implication \
for a Canadian fintech startup based on this week's data. Be specific and \
actionable — what should a founder actually do or watch out for?

Keep the total response under 800 words.
"""


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return anthropic.Anthropic(api_key=api_key)


async def summarise_article(
    title: str,
    content: str,
    url: str,
    source_name: str,
    max_content_chars: int = 4000,
) -> Optional[str]:
    """
    Summarise a single article into 3–5 bullet points using Claude.

    Returns the summary string or None on failure.
    Uses streaming to handle long outputs robustly.
    """
    # Truncate very long content to stay within token limits
    truncated = content[:max_content_chars]
    if len(content) > max_content_chars:
        truncated += "\n\n[Content truncated for brevity]"

    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        source_name=source_name,
        title=title,
        url=url,
        content=truncated,
    )

    try:
        client = _get_client()
        summary_parts: List[str] = []

        with client.messages.stream(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                summary_parts.append(text)

        summary = "".join(summary_parts).strip()
        logger.debug("Summarised '%s': %d chars", title[:60], len(summary))
        return summary

    except anthropic.RateLimitError:
        logger.warning("Rate limited by Anthropic API while summarising: %s", title[:60])
        return None
    except anthropic.APIStatusError as exc:
        logger.error("Anthropic API error (%s) for '%s': %s", exc.status_code, title[:60], exc.message)
        return None
    except anthropic.APIConnectionError:
        logger.error("Network error connecting to Anthropic API")
        return None
    except Exception as exc:
        logger.error("Unexpected error summarising '%s': %s", title[:60], exc)
        return None


async def generate_weekly_digest(updates: List[dict]) -> Optional[str]:
    """
    Generate a weekly digest from a list of update dicts.

    Each dict must have keys: title, source_name, summary, tags.
    Returns the digest text or None on failure.
    """
    if not updates:
        return "No updates found for the past week."

    # Build the input text for Claude
    lines = []
    for i, u in enumerate(updates[:20], 1):  # cap at 20 updates for token budget
        lines.append(
            f"{i}. [{u.get('source_name', 'Unknown')}] {u.get('title', 'Untitled')}\n"
            f"   Tags: {u.get('tags', '')}\n"
            f"   Summary: {u.get('summary') or '(no summary available)'}\n"
        )
    updates_text = "\n".join(lines)

    prompt = DIGEST_PROMPT_TEMPLATE.format(updates_text=updates_text)

    try:
        client = _get_client()
        digest_parts: List[str] = []

        with client.messages.stream(
            model=MODEL,
            max_tokens=1200,
            thinking={"type": "adaptive"},
            system=DIGEST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                digest_parts.append(text)

        return "".join(digest_parts).strip()

    except anthropic.RateLimitError:
        logger.warning("Rate limited generating weekly digest")
        return None
    except anthropic.APIStatusError as exc:
        logger.error("Anthropic API error generating digest: %s", exc.message)
        return None
    except anthropic.APIConnectionError:
        logger.error("Network error generating digest")
        return None
    except Exception as exc:
        logger.error("Unexpected error generating digest: %s", exc)
        return None
