"""Currents API news collector."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from langfuse import observe

from core.config import settings
from models.digest_schemas import RawCollectorItem
from .base import register_collector

logger = logging.getLogger(__name__)

CURRENTS_API_URL = "https://api.currentsapi.services/v1/latest-news"


class CurrentsCollector:
    name = "currents"

    @observe(name="currents_collector")
    async def collect(self) -> list[RawCollectorItem]:
        """Fetch latest news from Currents API."""
        api_key = settings.currents_api_key.strip()
        if not api_key:
            logger.info("Currents collector: no API key configured, skipping")
            return []

        params = {
            "apiKey": api_key,
            "language": "en",
            "page_size": 30,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(CURRENTS_API_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("Currents collector failed: %s", exc)
            return []

        items: list[RawCollectorItem] = []
        for article in data.get("news", []):
            title = article.get("title", "")
            if not title:
                continue

            published_at = None
            pub_str = article.get("published", "")
            if pub_str:
                try:
                    published_at = datetime.fromisoformat(
                        pub_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            items.append(RawCollectorItem(
                title=title,
                url=article.get("url", ""),
                source="currents",
                snippet=(article.get("description") or "")[:300],
                author=article.get("author"),
                published_at=published_at,
                extra={
                    "category": article.get("category", []),
                    "image": article.get("image"),
                },
            ))

        logger.info("Currents collector: %d articles", len(items))
        return items


register_collector(CurrentsCollector())
