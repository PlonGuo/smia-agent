"""Guardian Content API collector (parameterized — not auto-registered)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from langfuse import observe

from core.config import settings
from models.digest_schemas import RawCollectorItem

logger = logging.getLogger(__name__)

GUARDIAN_API_BASE = "https://content.guardianapis.com/search"


class GuardianCollector:
    """Fetches articles from the Guardian Content API.

    This collector is parameterized (sections, keywords) and instantiated
    per-topic at runtime via collector_factory — it does NOT auto-register.
    """

    def __init__(
        self,
        name: str = "guardian",
        sections: list[str] | None = None,
        keywords: list[str] | None = None,
    ):
        self._name = name
        self._sections = sections or ["world"]
        self._keywords = keywords

    @property
    def name(self) -> str:
        return self._name

    @observe(name="guardian_collector")
    async def collect(self) -> list[RawCollectorItem]:
        """Fetch recent articles from the Guardian API."""
        api_key = settings.guardian_api_key.strip()
        if not api_key:
            logger.warning("Guardian collector: no API key configured, skipping")
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        from_date = cutoff.strftime("%Y-%m-%d")

        all_items: list[RawCollectorItem] = []

        async with httpx.AsyncClient(timeout=15) as client:
            for section in self._sections:
                try:
                    items = await self._fetch_section(client, api_key, section, from_date)
                    all_items.extend(items)
                except Exception as exc:
                    logger.error("Guardian: failed to fetch section %s: %s", section, exc)

        logger.info("Guardian collector: %d articles from sections %s",
                     len(all_items), self._sections)
        return all_items

    async def _fetch_section(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        section: str,
        from_date: str,
    ) -> list[RawCollectorItem]:
        """Fetch articles from a single Guardian section."""
        params: dict = {
            "api-key": api_key,
            "section": section,
            "from-date": from_date,
            "page-size": 30,
            "show-fields": "trailText,byline",
            "order-by": "newest",
        }

        # Add keyword filter if configured
        if self._keywords:
            params["q"] = " OR ".join(self._keywords)

        response = await client.get(GUARDIAN_API_BASE, params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("response", {}).get("results", [])
        items: list[RawCollectorItem] = []

        for article in results:
            fields = article.get("fields", {})
            published_at = None
            pub_str = article.get("webPublicationDate", "")
            if pub_str:
                try:
                    published_at = datetime.fromisoformat(
                        pub_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            items.append(RawCollectorItem(
                title=article.get("webTitle", "Untitled"),
                url=article.get("webUrl", ""),
                source="guardian",
                snippet=(fields.get("trailText") or "")[:300],
                author=fields.get("byline"),
                published_at=published_at,
                extra={
                    "section": section,
                    "guardian_id": article.get("id", ""),
                },
            ))

        return items
