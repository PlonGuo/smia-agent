"""PydanticAI tools: fetch_reddit, fetch_youtube, fetch_amazon, clean_noise."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from langfuse import observe
from openai import AsyncOpenAI
from pydantic_ai import RunContext

from core.config import settings
from services.cache import get_cached_fetch, get_fetch_limits, set_cached_fetch
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


# ---------------------------------------------------------------------------
# LLM relevance filter (gpt-4o-mini)
# ---------------------------------------------------------------------------

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    """Lazy-init async OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.effective_openai_key)
    return _openai_client


@observe(name="relevance_filter")
async def relevance_filter(
    query: str,
    items: list[dict],
    source: str,
) -> tuple[list[dict], float]:
    """Batch LLM relevance check using gpt-4o-mini.

    Sends item titles + snippets to gpt-4o-mini, which returns a JSON array
    of booleans indicating whether each item is relevant to the query.

    Returns (relevant_items, yield_ratio).
    On any failure, returns (items, 1.0) — fail-open to avoid blocking pipeline.
    """
    if not items:
        return [], 1.0

    # Build numbered item list (title + first 200 chars of body/content)
    item_lines: list[str] = []
    for i, item in enumerate(items, 1):
        title = item.get("title", "Untitled")
        snippet = (
            item.get("body") or item.get("content") or item.get("description") or ""
        )[:200]
        item_lines.append(f"{i}. [{title}] {snippet}")

    prompt = (
        f'Query: "{query}"\n'
        f"Source: {source}\n\n"
        "For each item below, determine if it is relevant to the query. "
        "An item is relevant if it directly discusses, reviews, or mentions "
        "the specific product, brand, or topic in the query.\n\n"
        "Items:\n" + "\n".join(item_lines) + "\n\n"
        "Respond with ONLY a JSON array of booleans (true/false) — one per item. "
        "Example for 3 items: [true, false, true]"
    )

    try:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )
        raw = response.choices[0].message.content.strip()
        verdicts: list[bool] = json.loads(raw)

        if len(verdicts) != len(items):
            logger.warning(
                "Relevance filter returned %d verdicts for %d items — fail open",
                len(verdicts),
                len(items),
            )
            return items, 1.0

        relevant = [item for item, is_rel in zip(items, verdicts) if is_rel]
        yield_ratio = len(relevant) / len(items) if items else 1.0
        logger.info(
            "Relevance filter [%s]: %d/%d relevant (yield %.0f%%)",
            source,
            len(relevant),
            len(items),
            yield_ratio * 100,
        )
        return relevant, yield_ratio

    except Exception as exc:
        logger.warning("Relevance filter failed — returning all items: %s", exc)
        return items, 1.0


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


# ---------------------------------------------------------------------------
# Time range helpers
# ---------------------------------------------------------------------------

# Maps time_range to Reddit's time_filter parameter
_REDDIT_TIME_FILTER = {
    "day": "day",
    "week": "week",
    "month": "month",
    "year": "year",
}


def _youtube_published_after(time_range: str) -> str | None:
    """Compute ISO 8601 publishedAfter datetime for YouTube API."""
    deltas = {
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=30),
        "year": timedelta(days=365),
    }
    delta = deltas.get(time_range)
    if not delta:
        return None
    dt = datetime.now(timezone.utc) - delta
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Tool implementations with caching
# ---------------------------------------------------------------------------


async def fetch_reddit_tool(ctx: RunContext, query: str) -> str:
    """Fetch Reddit discussions about the given query.

    Searches Reddit using YARS, retrieves top posts and their comments,
    and returns a formatted text summary for LLM analysis.
    Applies relevance filtering with adaptive refetch on low yield.
    Uses per-source caching to avoid redundant fetches.
    """
    time_range = getattr(ctx.deps, "time_range", "week")
    limits = get_fetch_limits(time_range)
    initial_limit = limits["reddit"]
    reddit_time_filter = _REDDIT_TIME_FILTER.get(time_range, "week")

    # Check cache
    cached = get_cached_fetch(query, time_range, "reddit")
    if cached is not None:
        posts = cached
    else:
        posts = await fetch_reddit(query, limit=initial_limit, sort="relevance", time_filter=reddit_time_filter)
        if posts:
            set_cached_fetch(query, time_range, "reddit", posts)

    if not posts:
        return f"No Reddit results found for '{query}'."

    relevant, yield_ratio = await relevance_filter(query, posts, "reddit")

    # Adaptive refetch: if yield < 50% and we got a full batch, try 2x
    if yield_ratio < 0.5 and len(posts) >= initial_limit and cached is None:
        logger.info("Reddit yield %.0f%% — refetching with limit=%d", yield_ratio * 100, initial_limit * 2)
        posts = await fetch_reddit(query, limit=initial_limit * 2, sort="relevance", time_filter=reddit_time_filter)
        if posts:
            set_cached_fetch(query, time_range, "reddit", posts)
            relevant, yield_ratio = await relevance_filter(query, posts, "reddit")

    if not relevant:
        return f"No relevant Reddit results found for '{query}'."

    sections: list[str] = []
    for post in relevant:
        title = post.get("title", "Untitled")
        body = _clean_text(post.get("body", "")[:500], "reddit")
        url = post.get("url", "")
        comments_text = _summarize_comments(post.get("comments", []))
        if not body and not comments_text:
            continue
        sections.append(
            f"### {title}\nURL: {url}\n{body}\n\n**Comments:**\n{comments_text}"
        )

    if not sections:
        return f"No meaningful Reddit results found for '{query}'."

    return (
        f"# Reddit Results for '{query}' ({len(sections)} posts)\n\n"
        + "\n\n---\n\n".join(sections)
    )


async def fetch_youtube_tool(ctx: RunContext, query: str) -> str:
    """Fetch YouTube video comments about the given query.

    Searches YouTube Data API v3, retrieves top videos and their comments,
    and returns a formatted text summary for LLM analysis.
    Applies relevance filtering with adaptive refetch on low yield.
    Uses per-source caching to avoid redundant fetches.
    """
    time_range = getattr(ctx.deps, "time_range", "week")
    limits = get_fetch_limits(time_range)
    initial_limit = limits["youtube"]
    published_after = _youtube_published_after(time_range)

    # Check cache
    cached = get_cached_fetch(query, time_range, "youtube")
    if cached is not None:
        videos = cached
    else:
        videos = await fetch_youtube(query, max_videos=initial_limit, max_comments_per_video=15, published_after=published_after)
        if videos:
            set_cached_fetch(query, time_range, "youtube", videos)

    if not videos:
        return f"No YouTube results found for '{query}'."

    relevant, yield_ratio = await relevance_filter(query, videos, "youtube")

    if yield_ratio < 0.5 and len(videos) >= initial_limit and cached is None:
        logger.info("YouTube yield %.0f%% — refetching with limit=%d", yield_ratio * 100, initial_limit * 2)
        videos = await fetch_youtube(query, max_videos=initial_limit * 2, max_comments_per_video=15, published_after=published_after)
        if videos:
            set_cached_fetch(query, time_range, "youtube", videos)
            relevant, yield_ratio = await relevance_filter(query, videos, "youtube")

    if not relevant:
        return f"No relevant YouTube results found for '{query}'."

    sections: list[str] = []
    for video in relevant:
        title = video.get("title", "Untitled")
        channel = video.get("channel", "Unknown")
        url = video.get("url", "")
        desc = _clean_text(video.get("description", "")[:300], "youtube")
        comments_text = _summarize_comments(video.get("comments", []))
        sections.append(
            f"### {title} (by {channel})\nURL: {url}\n{desc}\n\n**Comments:**\n{comments_text}"
        )

    return (
        f"# YouTube Results for '{query}' ({len(sections)} videos)\n\n"
        + "\n\n---\n\n".join(sections)
    )


async def fetch_amazon_tool(ctx: RunContext, query: str) -> str:
    """Fetch Amazon product listings and reviews for the given query.

    Uses Crawl4AI (with Firecrawl fallback) to scrape Amazon search results
    and returns the extracted markdown content.
    Applies relevance filtering with adaptive refetch on low yield.
    Uses per-source caching to avoid redundant fetches.
    """
    time_range = getattr(ctx.deps, "time_range", "week")
    limits = get_fetch_limits(time_range)
    initial_max = limits["amazon"]

    # Check cache
    cached = get_cached_fetch(query, time_range, "amazon")
    if cached is not None:
        results = cached
    else:
        try:
            results = await fetch_amazon(query, max_products=initial_max)
        except RuntimeError as exc:
            logger.error("Amazon fetch error: %s", exc)
            return f"[ERROR] Failed to fetch Amazon data for '{query}': {exc}"
        if results:
            set_cached_fetch(query, time_range, "amazon", results)

    if not results:
        return f"No Amazon results found for '{query}'."

    relevant, yield_ratio = await relevance_filter(query, results, "amazon")

    if yield_ratio < 0.5 and len(results) >= initial_max and cached is None:
        logger.info("Amazon yield %.0f%% — refetching with max_products=%d", yield_ratio * 100, initial_max * 2)
        try:
            results = await fetch_amazon(query, max_products=initial_max * 2)
            if results:
                set_cached_fetch(query, time_range, "amazon", results)
                relevant, yield_ratio = await relevance_filter(query, results, "amazon")
        except RuntimeError as exc:
            logger.error("Amazon refetch error: %s", exc)

    if not relevant:
        return f"No relevant Amazon results found for '{query}'."

    sections: list[str] = []
    for item in relevant:
        title = item.get("title", "")
        content = _clean_text(item.get("content", "")[:5000], "amazon")
        sections.append(f"### {title}\n{content}")

    return f"# Amazon Results for '{query}'\n\n" + "\n\n---\n\n".join(sections)


async def clean_noise_tool(ctx: RunContext, data: str, source: str) -> str:
    """Remove irrelevant content (ads, spam, off-topic) from scraped data.

    Applies source-aware heuristic cleaning. This is already called automatically
    by the fetch tools, but can be called again if additional cleaning is needed.
    """
    return _clean_text(data, source)
