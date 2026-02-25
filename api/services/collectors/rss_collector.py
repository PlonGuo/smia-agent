"""RSS/Substack/Blog feed collector."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import mktime

import feedparser
from langfuse import observe

from models.digest_schemas import RawCollectorItem
from .base import register_collector

logger = logging.getLogger(__name__)

# Load feed URLs from config file (S2)
_config_path = Path(__file__).resolve().parent.parent.parent / "config" / "rss_feeds.json"


def _load_feeds() -> list[dict]:
    """Load RSS feed configuration from JSON file."""
    try:
        with open(_config_path) as f:
            return json.load(f)["feeds"]
    except Exception as exc:
        logger.error("Failed to load RSS feeds config: %s", exc)
        return []


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_feed_sync(feed_config: dict, cutoff: datetime) -> list[RawCollectorItem]:
    """Parse a single RSS feed synchronously. Returns items from last 48h."""
    try:
        parsed = feedparser.parse(feed_config["url"])
        if parsed.bozo and not parsed.entries:
            logger.warning("Malformed feed: %s", feed_config["name"])
            return []

        items = []
        for entry in parsed.entries:
            # Parse published date
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime.fromtimestamp(
                    mktime(entry.published_parsed), tz=timezone.utc
                )
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published_at = datetime.fromtimestamp(
                    mktime(entry.updated_parsed), tz=timezone.utc
                )

            # Skip entries older than cutoff
            if published_at and published_at < cutoff:
                continue

            # Extract snippet
            snippet = ""
            if hasattr(entry, "summary"):
                snippet = _strip_html(entry.summary)[:300]
            elif hasattr(entry, "description"):
                snippet = _strip_html(entry.description)[:300]

            items.append(RawCollectorItem(
                title=entry.get("title", "Untitled"),
                url=entry.get("link", ""),
                source="rss",
                snippet=snippet,
                author=entry.get("author") or feed_config["name"],
                published_at=published_at,
                extra={"feed_name": feed_config["name"]},
            ))
        return items

    except Exception as exc:
        logger.error("Failed to parse feed %s: %s", feed_config["name"], exc)
        return []


class RssCollector:
    name = "rss"

    @observe(name="rss_collector")
    async def collect(self) -> list[RawCollectorItem]:
        """Fetch recent entries from all configured RSS feeds.

        feedparser.parse() is synchronous — run in executor (I4).
        """
        feeds = _load_feeds()
        if not feeds:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        loop = asyncio.get_event_loop()

        # Parse all feeds in parallel using thread pool
        tasks = [
            loop.run_in_executor(None, _parse_feed_sync, feed, cutoff)
            for feed in feeds
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Feed %s failed: %s", feeds[i]["name"], result)
            else:
                all_items.extend(result)

        logger.info("RSS collector: %d entries from %d feeds", len(all_items), len(feeds))
        return all_items


register_collector(RssCollector())
