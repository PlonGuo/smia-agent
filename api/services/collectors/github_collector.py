"""GitHub trending AI/LLM repos via GitHub Search API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from langfuse import observe

from models.digest_schemas import RawCollectorItem
from .base import register_collector

logger = logging.getLogger(__name__)

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


class GithubCollector:
    name = "github"

    @observe(name="github_collector")
    async def collect(self) -> list[RawCollectorItem]:
        """Fetch trending AI/LLM repos created or updated recently."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    GITHUB_SEARCH_URL,
                    params={
                        "q": f"topic:ai OR topic:llm OR topic:machine-learning created:>{yesterday}",
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 30,
                    },
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "SmIA/1.0",
                    },
                )

                if response.status_code == 403:
                    logger.warning("GitHub API rate limited")
                    return []

                response.raise_for_status()
                data = response.json()

            items = []
            for repo in data.get("items", []):
                created_at = None
                if repo.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(
                            repo["created_at"].replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                items.append(RawCollectorItem(
                    title=repo["full_name"],
                    url=repo["html_url"],
                    source="github",
                    snippet=repo.get("description") or "",
                    author=repo.get("owner", {}).get("login"),
                    published_at=created_at,
                    extra={
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language"),
                    },
                ))

            logger.info("GitHub collector: %d repos", len(items))
            return items

        except Exception as exc:
            logger.error("GitHub collector failed: %s", exc)
            return []


register_collector(GithubCollector())
