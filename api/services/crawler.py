"""Crawler service: Reddit (YARS), YouTube (Data API v3), Amazon (Crawl4AI / Firecrawl)."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

# Max time (seconds) for any single crawl operation.
CRAWL_TIMEOUT = 45

# ---------------------------------------------------------------------------
# Reddit  (YARS – synchronous library, run in executor)
# ---------------------------------------------------------------------------

# Make the vendored YARS source importable.
_yars_src = Path(__file__).resolve().parent.parent.parent / "libs" / "yars" / "src"
if str(_yars_src) not in sys.path:
    sys.path.insert(0, str(_yars_src))


def _get_yars():
    """Lazy-import YARS to avoid import-time side effects (logging config)."""
    from yars.yars import YARS  # type: ignore[import-untyped]

    return YARS(timeout=CRAWL_TIMEOUT)


async def fetch_reddit(
    query: str,
    limit: int = 5,
    sort: str = "relevance",
    time_filter: str = "week",
) -> list[dict[str, Any]]:
    """Search Reddit and scrape post details using YARS.

    Returns a list of dicts:
        {title, body, comments, permalink, url, source}
    """

    def _sync_fetch() -> list[dict[str, Any]]:
        miner = _get_yars()
        search_results = miner.search_reddit(
            query, limit=limit, sort=sort, time_filter=time_filter
        )
        posts: list[dict[str, Any]] = []
        for result in search_results:
            try:
                details = miner.scrape_post_details(result["permalink"])
                if details:
                    posts.append(
                        {
                            "title": details.get("title", result.get("title", "")),
                            "body": details.get("body", ""),
                            "comments": details.get("comments", []),
                            "permalink": result.get("permalink", ""),
                            "url": result.get("link", ""),
                            "source": "reddit",
                        }
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to scrape Reddit post %s: %s",
                    result.get("permalink"),
                    exc,
                )
        return posts

    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _sync_fetch),
            timeout=CRAWL_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error("Reddit fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("Reddit fetch failed for query %s: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# YouTube  (Data API v3 via httpx)
# ---------------------------------------------------------------------------

_YT_SEARCH = "https://www.googleapis.com/youtube/v3/search"
_YT_COMMENTS = "https://www.googleapis.com/youtube/v3/commentThreads"


async def fetch_youtube(
    query: str,
    max_videos: int = 5,
    max_comments_per_video: int = 20,
) -> list[dict[str, Any]]:
    """Search YouTube and fetch comments for the top videos.

    Returns a list of dicts:
        {title, video_id, url, description, channel, published_at, comments, source}
    """
    api_key = settings.youtube_api_key
    if not api_key:
        logger.warning("YouTube API key not configured – skipping YouTube fetch")
        return []

    try:
        async with httpx.AsyncClient(timeout=CRAWL_TIMEOUT) as client:
            # 1. Search for videos
            search_resp = await client.get(
                _YT_SEARCH,
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": max_videos,
                    "order": "relevance",
                    "key": api_key,
                },
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])

            # 2. For each video, grab comments concurrently
            async def _video_with_comments(item: dict) -> dict[str, Any]:
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]
                comments = await _fetch_yt_comments(
                    client, video_id, api_key, max_comments_per_video
                )
                return {
                    "title": snippet.get("title", ""),
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "description": snippet.get("description", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "comments": comments,
                    "source": "youtube",
                }

            videos = await asyncio.gather(
                *[_video_with_comments(item) for item in items]
            )
            return list(videos)

    except httpx.TimeoutException:
        logger.error("YouTube fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("YouTube fetch failed for query %s: %s", query, exc)
        return []


async def _fetch_yt_comments(
    client: httpx.AsyncClient,
    video_id: str,
    api_key: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Fetch top-level comments for a YouTube video."""
    try:
        resp = await client.get(
            _YT_COMMENTS,
            params={
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(max_results, 100),
                "order": "relevance",
                "textFormat": "plainText",
                "key": api_key,
            },
        )
        resp.raise_for_status()
        return [
            {
                "author": c["snippet"]["topLevelComment"]["snippet"].get(
                    "authorDisplayName", ""
                ),
                "text": c["snippet"]["topLevelComment"]["snippet"].get(
                    "textDisplay", ""
                ),
                "likes": c["snippet"]["topLevelComment"]["snippet"].get(
                    "likeCount", 0
                ),
                "published_at": c["snippet"]["topLevelComment"]["snippet"].get(
                    "publishedAt", ""
                ),
            }
            for c in resp.json().get("items", [])
        ]
    except Exception as exc:
        logger.warning("Failed to fetch comments for video %s: %s", video_id, exc)
        return []


# ---------------------------------------------------------------------------
# Amazon  (Crawl4AI primary, Firecrawl fallback)
# ---------------------------------------------------------------------------


async def fetch_amazon(
    query: str,
    max_products: int = 3,
) -> list[dict[str, Any]]:
    """Scrape Amazon search results / reviews.

    Tries Crawl4AI first (headless browser), falls back to Firecrawl cloud API.

    Returns a list of dicts:
        {title, url, content, source}
    """
    search_url = f"https://www.amazon.com/s?k={quote_plus(query)}"

    # Try Crawl4AI
    content = await _crawl4ai_fetch(search_url)
    if content:
        return [
            {
                "title": f"Amazon results for: {query}",
                "url": search_url,
                "content": content,
                "source": "amazon",
            }
        ]

    # Fallback: Firecrawl
    content = await _firecrawl_fetch(search_url)
    if content:
        return [
            {
                "title": f"Amazon results for: {query}",
                "url": search_url,
                "content": content,
                "source": "amazon",
            }
        ]

    logger.error(
        "Both Crawl4AI and Firecrawl failed for Amazon query: %s", query
    )
    return []


async def _crawl4ai_fetch(url: str) -> str | None:
    """Scrape a URL using Crawl4AI (headless browser)."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_cfg = BrowserConfig(headless=True)
        run_cfg = CrawlerRunConfig(word_count_threshold=10)

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url=url, config=run_cfg),
                timeout=CRAWL_TIMEOUT,
            )
            if result.success and result.markdown:
                return result.markdown
            return None
    except ImportError:
        logger.warning("crawl4ai not installed – skipping")
        return None
    except asyncio.TimeoutError:
        logger.warning("Crawl4AI timed out for URL: %s", url)
        return None
    except Exception as exc:
        logger.warning("Crawl4AI failed for URL %s: %s", url, exc)
        return None


async def _firecrawl_fetch(url: str) -> str | None:
    """Scrape a URL using Firecrawl cloud API (async client)."""
    api_key = settings.firecrawl_api_key
    if not api_key:
        logger.warning("Firecrawl API key not configured – skipping fallback")
        return None

    try:
        from firecrawl import AsyncFirecrawlApp

        app = AsyncFirecrawlApp(api_key=api_key)
        document = await asyncio.wait_for(
            app.scrape_url(url),
            timeout=CRAWL_TIMEOUT,
        )
        return document.markdown if document else None
    except asyncio.TimeoutError:
        logger.warning("Firecrawl timed out for URL: %s", url)
        return None
    except Exception as exc:
        logger.warning("Firecrawl failed for URL %s: %s", url, exc)
        return None
