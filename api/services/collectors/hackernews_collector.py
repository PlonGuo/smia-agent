"""Hacker News collector via Algolia API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
from langfuse import observe

from models.digest_schemas import RawCollectorItem

from .base import register_collector

logger = logging.getLogger(__name__)

HN_ALGOLIA_URL = "http://hn.algolia.com/api/v1/search_by_date"


class HackernewsCollector:
    name = "hackernews"

    @observe(name="hackernews_collector")
    async def collect(self) -> list[RawCollectorItem]:
        """Fetch top stories from Hacker News (last 24h)."""
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        cutoff_ts = int(cutoff.timestamp())

        params = {
            "tags": "story",
            "hitsPerPage": 20,
            "numericFilters": f"created_at_i>{cutoff_ts}",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(HN_ALGOLIA_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("HackerNews collector failed: %s", exc)
            return []

        items: list[RawCollectorItem] = []
        for hit in data.get("hits", []):
            title = hit.get("title", "")
            if not title:
                continue

            # Use the article URL if available, fall back to HN discussion
            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"

            published_at = None
            created_str = hit.get("created_at", "")
            if created_str:
                try:
                    published_at = datetime.fromisoformat(
                        created_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            items.append(RawCollectorItem(
                title=title,
                url=story_url,
                source="hackernews",
                snippet=(hit.get("story_text") or "")[:300] if hit.get("story_text") else None,
                author=hit.get("author"),
                published_at=published_at,
                extra={
                    "hn_id": hit.get("objectID", ""),
                    "points": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                },
            ))

        logger.info("HackerNews collector: %d stories", len(items))
        return items


register_collector(HackernewsCollector())
