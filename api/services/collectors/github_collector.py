"""GitHub trending AI/LLM repos via GitHub Search API.

Strategy: find repos with AI-related topics that were recently pushed (active)
and already have meaningful star counts. This captures trending projects —
repos that exist AND are actively developed — rather than brand-new repos
that nobody has starred yet.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from langfuse import observe

from models.digest_schemas import RawCollectorItem
from .base import register_collector

logger = logging.getLogger(__name__)

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"

# Top starred repos with recent activity (pushed in last 7 days)
# This reliably returns 10+ results every day
_QUERIES = [
    "topic:ai pushed:>{since} stars:>100",
    "topic:llm pushed:>{since} stars:>50",
    "topic:machine-learning pushed:>{since} stars:>100",
]
_MAX_ITEMS = 10


class GithubCollector:
    name = "github"

    @observe(name="github_collector")
    async def collect(self) -> list[RawCollectorItem]:
        """Fetch top AI/LLM repos with recent activity, sorted by stars."""
        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        seen_urls: set[str] = set()
        all_items: list[RawCollectorItem] = []

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SmIA/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                for query_template in _QUERIES:
                    if len(all_items) >= _MAX_ITEMS:
                        break

                    query = query_template.format(since=since)
                    response = await client.get(
                        GITHUB_SEARCH_URL,
                        params={
                            "q": query,
                            "sort": "stars",
                            "order": "desc",
                            "per_page": 10,
                        },
                        headers=headers,
                    )

                    if response.status_code == 403:
                        logger.warning("GitHub API rate limited on query: %s", query)
                        continue

                    if response.status_code == 422:
                        logger.warning("GitHub API rejected query: %s", query)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    for repo in data.get("items", []):
                        url = repo["html_url"]
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        pushed_at = None
                        if repo.get("pushed_at"):
                            try:
                                pushed_at = datetime.fromisoformat(
                                    repo["pushed_at"].replace("Z", "+00:00")
                                )
                            except ValueError:
                                pass

                        all_items.append(RawCollectorItem(
                            title=repo["full_name"],
                            url=url,
                            source="github",
                            snippet=repo.get("description") or "",
                            author=repo.get("owner", {}).get("login"),
                            published_at=pushed_at,
                            extra={
                                "stars": repo.get("stargazers_count", 0),
                                "forks": repo.get("forks_count", 0),
                                "language": repo.get("language"),
                                "topics": repo.get("topics", [])[:5],
                            },
                        ))

                        if len(all_items) >= _MAX_ITEMS:
                            break

            logger.info("GitHub collector: %d repos", len(all_items))
            return all_items

        except Exception as exc:
            logger.error("GitHub collector failed: %s", exc)
            return []


register_collector(GithubCollector())
