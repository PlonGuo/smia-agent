"""PydanticAI tools: fetch_reddit, fetch_youtube, fetch_amazon, clean_noise."""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic_ai import RunContext

from services.crawler import fetch_amazon, fetch_reddit, fetch_youtube

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared cleaning helpers
# ---------------------------------------------------------------------------

_GENERAL_NOISE = [
    "subscribe to our newsletter",
    "click here to buy",
    "advertisement",
    "this is sponsored",
    "sponsored content",
    "sign up for free",
    "download our app",
]

_MARKDOWN_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MARKDOWN_LINK_JS_RE = re.compile(r"\[([^\]]*)\]\(javascript:[^)]*\)")
_AMAZON_NAV_RE = re.compile(
    r"(?i)^(back to top|get to know us|make money with us|"
    r"amazon payment products|let us help you|"
    r"›\s*see all|see top 100|audible|"
    r"conditions of use|privacy notice|"
    r"© \d{4}|amazon\.com, inc\.).*$",
    re.MULTILINE,
)


def _clean_text(text: str, source: str = "") -> str:
    """Apply source-aware cleaning to remove noise from scraped text."""
    if not text:
        return ""

    # Strip markdown image tags (adds no value for text analysis)
    text = _MARKDOWN_IMG_RE.sub("", text)

    # Replace JS links with just the link text
    text = _MARKDOWN_LINK_JS_RE.sub(r"\1", text)

    # Source-specific cleaning
    if source == "amazon":
        text = _AMAZON_NAV_RE.sub("", text)

    # General line-level cleaning
    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        # Skip empty lines in sequence (max 1 blank line)
        if not stripped:
            if cleaned and cleaned[-1].strip() == "":
                continue
            cleaned.append("")
            continue
        # Skip general noise
        if any(noise in lower for noise in _GENERAL_NOISE):
            continue
        # Skip Reddit deletions
        if source == "reddit" and stripped in ("[deleted]", "[removed]"):
            continue
        # Skip very short non-header lines
        if len(stripped) < 5 and not stripped.startswith("#"):
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def _summarize_comments(comments: list[dict], max_comments: int = 10) -> str:
    """Flatten nested Reddit/YouTube comments into a concise text block."""
    lines: list[str] = []
    for c in comments[:max_comments]:
        author = c.get("author", "anonymous")
        body = c.get("body") or c.get("text", "")
        score = c.get("score") or c.get("likes", "")

        # Skip empty/deleted comments
        body_stripped = body.strip()
        if not body_stripped or body_stripped in ("[deleted]", "[removed]"):
            continue

        lines.append(f"- [{author}] (score: {score}): {body[:300]}")
        for reply in c.get("replies", [])[:2]:
            r_author = reply.get("author", "anon")
            r_body = reply.get("body", "")[:200]
            if r_body.strip() and r_body.strip() not in ("[deleted]", "[removed]"):
                lines.append(f"  └─ [{r_author}]: {r_body}")
    return "\n".join(lines)


async def fetch_reddit_tool(ctx: RunContext[str], query: str) -> str:
    """Fetch Reddit discussions about the given query.

    Searches Reddit using YARS, retrieves top posts and their comments,
    and returns a formatted text summary for LLM analysis.
    """
    posts = await fetch_reddit(query, limit=5, sort="relevance", time_filter="week")
    if not posts:
        return f"No Reddit results found for '{query}'."

    sections: list[str] = []
    for post in posts:
        title = post.get("title", "Untitled")
        body = _clean_text(post.get("body", "")[:500], "reddit")
        url = post.get("url", "")
        comments_text = _summarize_comments(post.get("comments", []))
        if not body and not comments_text:
            continue  # Skip posts with no meaningful content
        sections.append(
            f"### {title}\nURL: {url}\n{body}\n\n**Comments:**\n{comments_text}"
        )

    if not sections:
        return f"No meaningful Reddit results found for '{query}'."

    return (
        f"# Reddit Results for '{query}' ({len(sections)} posts)\n\n"
        + "\n\n---\n\n".join(sections)
    )


async def fetch_youtube_tool(ctx: RunContext[str], query: str) -> str:
    """Fetch YouTube video comments about the given query.

    Searches YouTube Data API v3, retrieves top videos and their comments,
    and returns a formatted text summary for LLM analysis.
    """
    videos = await fetch_youtube(query, max_videos=5, max_comments_per_video=15)
    if not videos:
        return f"No YouTube results found for '{query}'."

    sections: list[str] = []
    for video in videos:
        title = video.get("title", "Untitled")
        channel = video.get("channel", "Unknown")
        url = video.get("url", "")
        desc = _clean_text(video.get("description", "")[:300], "youtube")
        comments_text = _summarize_comments(video.get("comments", []))
        sections.append(
            f"### {title} (by {channel})\nURL: {url}\n{desc}\n\n**Comments:**\n{comments_text}"
        )

    return (
        f"# YouTube Results for '{query}' ({len(videos)} videos)\n\n"
        + "\n\n---\n\n".join(sections)
    )


async def fetch_amazon_tool(ctx: RunContext[str], query: str) -> str:
    """Fetch Amazon product listings and reviews for the given query.

    Uses Crawl4AI (with Firecrawl fallback) to scrape Amazon search results
    and returns the extracted markdown content.
    """
    try:
        results = await fetch_amazon(query, max_products=3)
    except RuntimeError as exc:
        logger.error("Amazon fetch error: %s", exc)
        return f"[ERROR] Failed to fetch Amazon data for '{query}': {exc}"

    if not results:
        return f"No Amazon results found for '{query}'."

    sections: list[str] = []
    for item in results:
        title = item.get("title", "")
        content = _clean_text(item.get("content", "")[:5000], "amazon")
        sections.append(f"### {title}\n{content}")

    return f"# Amazon Results for '{query}'\n\n" + "\n\n---\n\n".join(sections)


async def clean_noise_tool(ctx: RunContext[str], data: str, source: str) -> str:
    """Remove irrelevant content (ads, spam, off-topic) from scraped data.

    Applies source-aware heuristic cleaning. This is already called automatically
    by the fetch tools, but can be called again if additional cleaning is needed.
    """
    return _clean_text(data, source)
