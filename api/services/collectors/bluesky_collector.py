"""Bluesky posts from AI researchers via AT Protocol API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from langfuse import observe

from core.config import settings
from models.digest_schemas import RawCollectorItem
from .base import register_collector

logger = logging.getLogger(__name__)

# AT Protocol public API
BSKY_API_BASE = "https://public.api.bsky.app"

# AI researchers to follow on Bluesky
AI_RESEARCHER_HANDLES = [
    "yolanda.bsky.social",       # Yolanda Gil
    "emollick.bsky.social",      # Ethan Mollick
    "ylecun.bsky.social",        # Yann LeCun
    "fchollet.bsky.social",      # Francois Chollet
    "karpathy.bsky.social",      # Andrej Karpathy
    "hardmaru.bsky.social",      # David Ha
    "swyx.bsky.social",          # swyx
    "simonw.net",                # Simon Willison
    "lilianweng.bsky.social",    # Lilian Weng
    "jimfan.bsky.social",        # Jim Fan
    "alexalbert.bsky.social",    # Alex Albert
    "bengoldhaber.com",          # Ben Goldhaber
    "natolambert.bsky.social",   # Nathan Lambert
    "huggingface.bsky.social",   # Hugging Face
    "langchain.bsky.social",     # LangChain
]


class BlueskyCollector:
    name = "bluesky"

    @observe(name="bluesky_collector")
    async def collect(self) -> list[RawCollectorItem]:
        """Fetch recent posts from AI researchers on Bluesky."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        all_items: list[RawCollectorItem] = []

        async with httpx.AsyncClient(timeout=15) as client:
            for handle in AI_RESEARCHER_HANDLES:
                try:
                    items = await self._fetch_author_feed(client, handle, cutoff)
                    all_items.extend(items)
                except Exception as exc:
                    logger.warning("Bluesky: failed to fetch %s: %s", handle, exc)
                    continue

        logger.info("Bluesky collector: %d posts from %d handles",
                     len(all_items), len(AI_RESEARCHER_HANDLES))
        return all_items

    async def _fetch_author_feed(
        self, client: httpx.AsyncClient, handle: str, cutoff: datetime
    ) -> list[RawCollectorItem]:
        """Fetch recent posts from a single Bluesky author."""
        response = await client.get(
            f"{BSKY_API_BASE}/xrpc/app.bsky.feed.getAuthorFeed",
            params={"actor": handle, "limit": 10, "filter": "posts_no_replies"},
        )

        if response.status_code != 200:
            return []

        data = response.json()
        items = []

        for feed_item in data.get("feed", []):
            post = feed_item.get("post", {})
            record = post.get("record", {})
            text = record.get("text", "")

            if not text:
                continue

            # Parse created timestamp
            created_at_str = record.get("createdAt", "")
            published_at = None
            if created_at_str:
                try:
                    published_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            # Skip old posts
            if published_at and published_at < cutoff:
                continue

            # Build Bluesky post URL
            author_did = post.get("author", {}).get("did", "")
            uri = post.get("uri", "")
            rkey = uri.split("/")[-1] if "/" in uri else ""
            author_handle = post.get("author", {}).get("handle", handle)
            post_url = f"https://bsky.app/profile/{author_handle}/post/{rkey}"

            # Extract embedded link if present
            embed_url = None
            embed = post.get("embed") or {}
            if embed.get("$type") == "app.bsky.embed.external#view":
                external = embed.get("external", {})
                embed_url = external.get("uri")

            items.append(RawCollectorItem(
                title=text[:120].strip(),
                url=embed_url or post_url,
                source="bluesky",
                snippet=text[:300].strip(),
                author=author_handle,
                published_at=published_at,
                extra={"post_url": post_url},
            ))

        return items


register_collector(BlueskyCollector())
