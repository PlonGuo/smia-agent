"""arXiv cs.AI + cs.LG papers from last 24h."""

from __future__ import annotations

import asyncio
import logging

import arxiv
from langfuse import observe

from models.digest_schemas import RawCollectorItem
from .base import register_collector

logger = logging.getLogger(__name__)


class ArxivCollector:
    name = "arxiv"

    @observe(name="arxiv_collector")
    async def collect(self) -> list[RawCollectorItem]:
        """Fetch recent AI/ML papers from arXiv.

        arxiv lib is synchronous — run in executor to avoid blocking (I4).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._collect_sync)

    def _collect_sync(self) -> list[RawCollectorItem]:
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query="cat:cs.AI OR cat:cs.LG",
                max_results=50,
                sort_by=arxiv.SortCriterion.SubmittedDate,
            )
            items = []
            for result in client.results(search):
                items.append(RawCollectorItem(
                    title=result.title.strip().replace("\n", " "),
                    url=str(result.entry_id),
                    source="arxiv",
                    snippet=result.summary[:300].strip().replace("\n", " "),
                    author=str(result.authors[0]) if result.authors else None,
                    published_at=result.published,
                ))
            logger.info("arXiv collector: %d papers", len(items))
            return items
        except Exception as exc:
            logger.error("arXiv collector failed: %s", exc)
            return []


register_collector(ArxivCollector())
