"""PydanticAI tools: fetch_reddit, fetch_youtube, fetch_amazon, clean_noise."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext

from services.crawler import fetch_amazon, fetch_reddit, fetch_youtube

logger = logging.getLogger(__name__)


def _summarize_comments(comments: list[dict], max_comments: int = 10) -> str:
    """Flatten nested Reddit/YouTube comments into a concise text block."""
    lines: list[str] = []
    for c in comments[:max_comments]:
        author = c.get("author", "anonymous")
        body = c.get("body") or c.get("text", "")
        score = c.get("score") or c.get("likes", "")
        lines.append(f"- [{author}] (score: {score}): {body[:300]}")
        for reply in c.get("replies", [])[:2]:
            r_author = reply.get("author", "anon")
            r_body = reply.get("body", "")[:200]
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
        body = post.get("body", "")[:500]
        url = post.get("url", "")
        comments_text = _summarize_comments(post.get("comments", []))
        sections.append(
            f"### {title}\nURL: {url}\n{body}\n\n**Comments:**\n{comments_text}"
        )

    return (
        f"# Reddit Results for '{query}' ({len(posts)} posts)\n\n"
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
        desc = video.get("description", "")[:300]
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
    results = await fetch_amazon(query, max_products=3)
    if not results:
        return f"No Amazon results found for '{query}'."

    sections: list[str] = []
    for item in results:
        title = item.get("title", "")
        content = item.get("content", "")[:3000]
        sections.append(f"### {title}\n{content}")

    return f"# Amazon Results for '{query}'\n\n" + "\n\n---\n\n".join(sections)


async def clean_noise_tool(ctx: RunContext[str], data: str, source: str) -> str:
    """Remove irrelevant content (ads, spam, off-topic) from scraped data.

    This is a lightweight heuristic filter. The LLM itself does the heavy
    semantic filtering during the final analysis step.
    """
    if not data:
        return ""

    noise_indicators = [
        "subscribe to our newsletter",
        "click here to buy",
        "sponsored",
        "advertisement",
        "[deleted]",
        "[removed]",
    ]

    lines = data.split("\n")
    cleaned: list[str] = []
    for line in lines:
        lower = line.lower().strip()
        if not lower:
            cleaned.append(line)
            continue
        if any(noise in lower for noise in noise_indicators):
            continue
        if len(lower) < 5 and not lower.startswith("#"):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)
