"""Crawler service: Reddit (YARS), YouTube (Data API v3), Amazon (Crawl4AI / Firecrawl)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
from langfuse import observe

from core.config import settings

logger = logging.getLogger(__name__)

# Max time (seconds) for any single crawl operation.
CRAWL_TIMEOUT = 60

# ---------------------------------------------------------------------------
# Reddit  (YARS – synchronous library, run in executor)
# ---------------------------------------------------------------------------

# Make the vendored YARS source importable.
_yars_src = Path(__file__).resolve().parent.parent.parent / "libs" / "yars" / "src"
if str(_yars_src) not in sys.path:
    sys.path.insert(0, str(_yars_src))


def _get_yars():
    """Lazy-import YARS to avoid import-time side effects (logging config).

    When SCRAPER_API_KEY is configured, passes a ScraperAPI proxy to YARS
    so Reddit requests aren't blocked by datacenter IP restrictions.
    """
    from yars.yars import YARS  # type: ignore[import-untyped]

    proxy = None
    api_key = settings.scraper_api_key.strip()
    if api_key:
        proxy = f"http://scraperapi:{api_key}@proxy-server.scraperapi.com:8001"
        logger.info("YARS using ScraperAPI proxy")

    return YARS(proxy=proxy, timeout=CRAWL_TIMEOUT)


@observe(name="fetch_reddit")
async def fetch_reddit(
    query: str,
    limit: int = 5,
    sort: str = "relevance",
    time_filter: str = "week",
) -> list[dict[str, Any]]:
    """Search Reddit and scrape post details using YARS.

    Returns a list of dicts:
        {title, body, comments, permalink, url, source}

    When using a proxy, only scrapes details for the top 3 posts to stay
    within Vercel's 60s function timeout.
    """
    using_proxy = bool(settings.scraper_api_key.strip())

    def _sync_fetch() -> list[dict[str, Any]]:
        miner = _get_yars()
        search_results = miner.search_reddit(
            query, limit=limit, sort=sort, time_filter=time_filter
        )
        posts: list[dict[str, Any]] = []
        # When using proxy, limit detail scrapes to save time/credits
        detail_limit = 3 if using_proxy else limit
        for i, result in enumerate(search_results):
            if i < detail_limit:
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
                        continue
                except Exception as exc:
                    logger.warning(
                        "Failed to scrape Reddit post %s: %s",
                        result.get("permalink"),
                        exc,
                    )
            # Use search result data directly (no detail scrape)
            posts.append(
                {
                    "title": result.get("title", ""),
                    "body": result.get("description", ""),
                    "comments": [],
                    "permalink": result.get("permalink", ""),
                    "url": result.get("link", ""),
                    "source": "reddit",
                }
            )
        return posts

    try:
        timeout = 30 if using_proxy else CRAWL_TIMEOUT
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _sync_fetch),
            timeout=timeout,
        )
    except TimeoutError:
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


@observe(name="fetch_youtube")
async def fetch_youtube(
    query: str,
    max_videos: int = 5,
    max_comments_per_video: int = 20,
    published_after: str | None = None,
) -> list[dict[str, Any]]:
    """Search YouTube and fetch comments for the top videos.

    Args:
        published_after: ISO 8601 datetime string (e.g. "2026-02-13T00:00:00Z").
            When provided, only returns videos published after this date.

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
            params: dict[str, Any] = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_videos,
                "order": "relevance",
                "key": api_key,
            }
            if published_after:
                params["publishedAfter"] = published_after
            search_resp = await client.get(
                _YT_SEARCH,
                params=params,
            )
            search_resp.raise_for_status()
            items = [
                i for i in search_resp.json().get("items", [])
                if i.get("id", {}).get("videoId")
            ]

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
# Amazon  (Crawl4AI local, Firecrawl on serverless / fallback)
# ---------------------------------------------------------------------------

# Cache crawl4ai availability so we don't attempt imports on every call.
_crawl4ai_available: bool | None = None


def _has_crawl4ai() -> bool:
    """Check once whether crawl4ai is importable."""
    global _crawl4ai_available
    if _crawl4ai_available is None:
        try:
            import crawl4ai  # noqa: F401

            _crawl4ai_available = True
        except ImportError:
            _crawl4ai_available = False
    return _crawl4ai_available


async def _smart_fetch(url: str) -> str | None:
    """Fetch a URL using the best available crawler.

    Tries Crawl4AI first (local dev with browser), falls back to Firecrawl.
    Skips Crawl4AI entirely when it's not installed (e.g. Vercel serverless).
    """
    if _has_crawl4ai():
        content = await _crawl4ai_fetch(url)
        if content:
            return content
    return await _firecrawl_fetch(url)


@observe(name="fetch_amazon")
async def fetch_amazon(
    query: str,
    max_products: int = 2,
) -> list[dict[str, Any]]:
    """Scrape Amazon search results and individual product pages for reviews.

    1. Crawls the Amazon search page to get raw markdown
    2. Extracts product page URLs (/dp/ASIN patterns)
    3. Scrapes individual product pages for review content

    Returns a list of dicts:
        {title, url, content, source}

    Raises RuntimeError when all crawlers fail.
    """
    search_url = f"https://www.amazon.com/s?k={quote_plus(query)}"

    # Step 1: Crawl the search results page
    search_content = await _smart_fetch(search_url)
    if not search_content:
        raise RuntimeError(
            f"Amazon crawling failed for '{query}': no data returned. "
            "Ensure FIRECRAWL_API_KEY is set or crawl4ai is installed locally."
        )

    # Step 2: Extract product page URLs from the search results
    product_urls = _extract_amazon_product_urls(search_content, max_products)
    if not product_urls:
        # No product links found — return raw search content as fallback
        return [
            {
                "title": f"Amazon search results for: {query}",
                "url": search_url,
                "content": _trim_amazon_page(search_content),
                "source": "amazon",
            }
        ]

    # Step 3: Scrape individual product pages for reviews (parallel for Firecrawl)
    results = await _scrape_product_pages(product_urls)
    return results if results else [
        {
            "title": f"Amazon search results for: {query}",
            "url": search_url,
            "content": _trim_amazon_page(search_content),
            "source": "amazon",
        }
    ]


def _extract_amazon_product_urls(
    search_markdown: str,
    max_urls: int = 3,
) -> list[str]:
    """Extract Amazon product page URLs from search results markdown."""
    # Match Amazon product URLs (dp/ pattern)
    pattern = r"https?://(?:www\.)?amazon\.com/[^\s\)\"]*?/dp/[A-Z0-9]{10}"
    matches = re.findall(pattern, search_markdown)

    # Deduplicate while preserving order
    seen: set[str] = set()
    urls: list[str] = []
    for url in matches:
        base = url.split("?")[0].split("#")[0]
        if base not in seen:
            seen.add(base)
            urls.append(base)
        if len(urls) >= max_urls:
            break
    return urls


async def _scrape_product_pages(
    urls: list[str],
) -> list[dict[str, Any]]:
    """Scrape individual Amazon product pages for reviews and details."""

    async def _scrape_one(url: str) -> dict[str, Any] | None:
        content = await _smart_fetch(url)
        if not content:
            logger.warning("Could not scrape product page: %s", url)
            return None

        # Extract readable title from URL slug
        parts = url.split("/dp/")
        title = parts[0].rsplit("/", 1)[-1].replace("-", " ") if len(parts) > 1 else url

        return {
            "title": title,
            "url": url,
            "content": _trim_amazon_page(content),
            "source": "amazon",
        }

    # When using Firecrawl (cloud API), scrape in parallel for speed.
    # With Crawl4AI (local browser), scrape sequentially to avoid throttling.
    if _has_crawl4ai():
        results: list[dict[str, Any]] = []
        for u in urls:
            r = await _scrape_one(u)
            if r:
                results.append(r)
        return results
    else:
        scraped = await asyncio.gather(*[_scrape_one(u) for u in urls])
        return [r for r in scraped if r]


def _trim_amazon_page(content: str, max_chars: int = 8000) -> str:
    """Extract the most review-relevant portions of an Amazon product page.

    Amazon pages contain:
    - "Customers say" — AI-generated review summary with aspect ratings
    - "Top reviews from the United States" — individual user reviews
    - "Top reviews from other countries" — international reviews
    """
    sections: list[str] = []

    # 1. "Customers say" — AI-generated summary (grab up to 2000 chars from start)
    cs_match = re.search(r"(?i)#{2,4}\s*Customers say", content)
    if cs_match:
        # Find where the next major section starts
        us_match = re.search(r"(?i)Top reviews from the United States", content[cs_match.start():])
        end = cs_match.start() + (us_match.start() if us_match else 2000)
        sections.append(content[cs_match.start():end].strip()[:2000])

    # 2. "Top reviews from the United States" — individual reviews (up to 4000 chars)
    us_match = re.search(r"(?i)#{2,4}\s*Top reviews from the United States", content)
    if us_match:
        intl_match = re.search(r"(?i)#{2,4}\s*Top reviews from other countries", content[us_match.start():])
        end = us_match.start() + (intl_match.start() if intl_match else 5000)
        sections.append(content[us_match.start():end].strip()[:4000])

    # 3. "Top reviews from other countries" (optional, if we have budget left)
    intl_match = re.search(r"(?i)#{2,4}\s*Top reviews from other countries", content)
    if intl_match and len("\n\n".join(sections)) < max_chars - 2000:
        sections.append(content[intl_match.start():intl_match.start() + 2000].strip())

    if sections:
        return "\n\n".join(sections)[:max_chars]

    # Fallback: return the latter portion (reviews are usually below the fold)
    if len(content) > max_chars * 2:
        return content[len(content) // 2:][:max_chars]
    return content[:max_chars]


async def _crawl4ai_fetch(url: str) -> str | None:
    """Scrape a URL using Crawl4AI (headless browser)."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_cfg = BrowserConfig(
            headless=True,
            enable_stealth=True,
            user_agent_mode="random",
            viewport_width=1280,
            viewport_height=800,
        )
        run_cfg = CrawlerRunConfig(
            word_count_threshold=10,
            wait_until="domcontentloaded",
            delay_before_return_html=2.0,
            page_timeout=CRAWL_TIMEOUT * 1000,
            magic=True,
            scan_full_page=True,
            remove_overlay_elements=True,
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url=url, config=run_cfg),
                timeout=CRAWL_TIMEOUT + 10,
            )
            if result.success and result.markdown:
                return result.markdown
            logger.warning("Crawl4AI returned no content for URL: %s", url)
            return None
    except ImportError:
        logger.warning("crawl4ai not installed – skipping")
        return None
    except TimeoutError:
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
    except TimeoutError:
        logger.warning("Firecrawl timed out for URL: %s", url)
        return None
    except Exception as exc:
        logger.warning("Firecrawl failed for URL %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Hacker News  (Algolia API)
# ---------------------------------------------------------------------------

_HN_SEARCH = "http://hn.algolia.com/api/v1/search"
_HN_ITEM = "http://hn.algolia.com/api/v1/items"


@observe(name="fetch_hackernews")
async def fetch_hackernews(
    query: str,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Search Hacker News via Algolia API and fetch comments for top results.

    Returns a list of dicts:
        {title, url, body, comments, score, source}
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                _HN_SEARCH,
                params={"query": query, "tags": "story", "hitsPerPage": limit},
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])

            async def _enrich(hit: dict) -> dict[str, Any]:
                """Fetch comments for a single HN story."""
                comments: list[dict[str, str]] = []
                try:
                    item_resp = await client.get(f"{_HN_ITEM}/{hit['objectID']}")
                    item_resp.raise_for_status()
                    children = item_resp.json().get("children", [])
                    for child in children[:5]:
                        text = child.get("text") or ""
                        # Strip HTML tags from HN comment text
                        text = re.sub(r"<[^>]+>", "", text)
                        comments.append({
                            "author": child.get("author", ""),
                            "text": text[:200],
                        })
                except Exception as exc:
                    logger.warning("Failed to fetch HN comments for %s: %s", hit.get("objectID"), exc)

                story_text = hit.get("story_text") or hit.get("comment_text") or ""
                story_text = re.sub(r"<[^>]+>", "", story_text)

                return {
                    "title": hit.get("title", ""),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "body": story_text[:400],
                    "comments": comments,
                    "score": hit.get("points", 0),
                    "source": "hackernews",
                }

            # Enrich top 5 with comments, rest without
            enriched = await asyncio.gather(*[_enrich(h) for h in hits[:5]])
            plain = [
                {
                    "title": h.get("title", ""),
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}",
                    "body": re.sub(r"<[^>]+>", "", h.get("story_text") or "")[:400],
                    "comments": [],
                    "score": h.get("points", 0),
                    "source": "hackernews",
                }
                for h in hits[5:]
            ]
            return list(enriched) + plain

    except httpx.TimeoutException:
        logger.error("Hacker News fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("Hacker News fetch failed for query %s: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# DEV.to  (Forem API)
# ---------------------------------------------------------------------------

_DEVTO_ARTICLES = "https://dev.to/api/articles"
_DEVTO_COMMENTS = "https://dev.to/api/comments"


@observe(name="fetch_devto")
async def fetch_devto(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch articles from DEV.to by tag and top comments.

    Returns a list of dicts:
        {title, url, body, comments, score, source}
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                _DEVTO_ARTICLES,
                params={"tag": query, "per_page": limit, "top": 7},
            )
            resp.raise_for_status()
            articles = resp.json()

            async def _with_comments(article: dict) -> dict[str, Any]:
                """Fetch comments for a single DEV.to article."""
                comments: list[dict[str, str]] = []
                try:
                    c_resp = await client.get(
                        _DEVTO_COMMENTS,
                        params={"a_id": article["id"]},
                    )
                    c_resp.raise_for_status()
                    for c in c_resp.json()[:5]:
                        comments.append({
                            "author": c.get("user", {}).get("username", ""),
                            "text": re.sub(r"<[^>]+>", "", c.get("body_html", ""))[:200],
                        })
                except Exception as exc:
                    logger.warning("Failed to fetch DEV.to comments for article %s: %s", article.get("id"), exc)

                body = article.get("body_markdown") or article.get("description") or ""
                return {
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "body": body[:400],
                    "comments": comments,
                    "score": article.get("positive_reactions_count", 0),
                    "source": "devto",
                }

            # Enrich top 5 with comments, rest without
            enriched = await asyncio.gather(*[_with_comments(a) for a in articles[:5]])
            plain = [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "body": (a.get("description") or "")[:400],
                    "comments": [],
                    "score": a.get("positive_reactions_count", 0),
                    "source": "devto",
                }
                for a in articles[5:]
            ]
            return list(enriched) + plain

    except httpx.TimeoutException:
        logger.error("DEV.to fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("DEV.to fetch failed for query %s: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# News RSS  (feedparser, sync library run in executor)
# ---------------------------------------------------------------------------

_NEWS_RSS_FEEDS_PATH = Path(__file__).resolve().parent.parent / "config" / "news_rss_feeds.json"


@observe(name="fetch_news_rss")
async def fetch_news_rss(
    query: str,
    feeds: list[dict[str, str]] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch and filter RSS feed entries matching the query.

    Args:
        feeds: List of {name, url} dicts. If None, loads from rss_feeds.json.
        limit: Max entries to return across all feeds.

    Returns a list of dicts:
        {title, url, body, source, published_at}
    """
    if feeds is None:
        try:
            with open(_NEWS_RSS_FEEDS_PATH) as f:
                feeds = json.load(f).get("feeds", [])
        except Exception as exc:
            logger.error("Failed to load RSS feeds config: %s", exc)
            return []

    def _sync_parse() -> list[dict[str, Any]]:
        import feedparser  # type: ignore[import-untyped]

        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for feed_info in feeds:  # type: ignore[union-attr]
            try:
                parsed = feedparser.parse(feed_info["url"])
                for entry in parsed.entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    if query_lower in title.lower() or query_lower in summary.lower():
                        results.append({
                            "title": title,
                            "url": entry.get("link", ""),
                            "body": re.sub(r"<[^>]+>", "", summary)[:400],
                            "source": "news_rss",
                            "published_at": entry.get("published", ""),
                        })
                        if len(results) >= limit:
                            return results
            except Exception as exc:
                logger.warning("Failed to parse RSS feed %s: %s", feed_info.get("name"), exc)

        return results

    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _sync_parse),
            timeout=CRAWL_TIMEOUT,
        )
    except TimeoutError:
        logger.error("RSS feed fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("RSS feed fetch failed for query %s: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# Stack Exchange  (Stack Overflow API v2.3)
# ---------------------------------------------------------------------------

_SE_SEARCH = "https://api.stackexchange.com/2.3/search/advanced"


@observe(name="fetch_stackexchange")
async def fetch_stackexchange(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search Stack Overflow for relevant Q&A.

    Returns a list of dicts:
        {title, url, body, score, source}
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                _SE_SEARCH,
                params={
                    "q": query,
                    "site": "stackoverflow",
                    "sort": "relevance",
                    "pagesize": limit,
                    "filter": "withbody",
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

            results: list[dict[str, Any]] = []
            for item in items:
                body = item.get("body", "")
                body = re.sub(r"<[^>]+>", "", body)  # strip HTML tags
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "body": body[:400],
                    "score": item.get("score", 0),
                    "source": "stackexchange",
                })
            return results

    except httpx.TimeoutException:
        logger.error("StackExchange fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("StackExchange fetch failed for query %s: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# The Guardian  (Content API)
# ---------------------------------------------------------------------------

_GUARDIAN_SEARCH = "https://content.guardianapis.com/search"


@observe(name="fetch_guardian")
async def fetch_guardian(
    query: str,
    limit: int = 10,
    section: str | None = None,
) -> list[dict[str, Any]]:
    """Search The Guardian for news articles.

    Requires settings.guardian_api_key. Returns empty list if not configured.

    Returns a list of dicts:
        {title, url, body, source}
    """
    api_key = getattr(settings, "guardian_api_key", None)
    if not api_key:
        logger.info("Guardian API key not configured – skipping Guardian fetch")
        return []

    try:
        params: dict[str, Any] = {
            "q": query,
            "show-fields": "headline,bodyText,byline",
            "page-size": limit,
            "order-by": "newest",
            "api-key": api_key,
        }
        if section:
            params["section"] = section

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(_GUARDIAN_SEARCH, params=params)
            resp.raise_for_status()
            data = resp.json().get("response", {})
            articles = data.get("results", [])

            results: list[dict[str, Any]] = []
            for article in articles:
                fields = article.get("fields", {})
                results.append({
                    "title": fields.get("headline", article.get("webTitle", "")),
                    "url": article.get("webUrl", ""),
                    "body": (fields.get("bodyText") or "")[:400],
                    "source": "guardian",
                })
            return results

    except httpx.TimeoutException:
        logger.error("Guardian fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("Guardian fetch failed for query %s: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# Tavily  (AI search API)
# ---------------------------------------------------------------------------


@observe(name="fetch_tavily")
async def fetch_tavily(
    query: str,
    limit: int = 10,
    topic: str = "general",
) -> list[dict[str, Any]]:
    """Search the web using Tavily AI search.

    Requires settings.tavily_api_key. Returns empty list if not configured.

    Returns a list of dicts:
        {title, url, body, score, source}
    """
    api_key = getattr(settings, "tavily_api_key", None)
    if not api_key:
        logger.info("Tavily API key not configured – skipping Tavily fetch")
        return []

    try:
        from tavily import AsyncTavilyClient  # type: ignore[import-untyped]

        client = AsyncTavilyClient(api_key=api_key)
        response = await asyncio.wait_for(
            client.search(query, max_results=limit, topic=topic),
            timeout=30,
        )
        results: list[dict[str, Any]] = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "body": (item.get("content") or "")[:400],
                "score": item.get("score", 0),
                "source": "tavily",
            })
        return results

    except ImportError:
        logger.warning("tavily-python not installed – skipping Tavily fetch")
        return []
    except TimeoutError:
        logger.error("Tavily fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("Tavily fetch failed for query %s: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# Currents API  (news aggregation)
# ---------------------------------------------------------------------------

_CURRENTS_SEARCH = "https://api.currentsapi.services/v1/search"


@observe(name="fetch_currents_news")
async def fetch_currents_news(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search news articles via Currents API.

    Requires settings.currents_api_key. Returns empty list if not configured.

    Returns a list of dicts:
        {title, url, body, source}
    """
    api_key = getattr(settings, "currents_api_key", None)
    if not api_key:
        logger.info("Currents API key not configured – skipping Currents fetch")
        return []

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                _CURRENTS_SEARCH,
                params={
                    "keywords": query,
                    "language": "en",
                    "apiKey": api_key,
                },
            )
            resp.raise_for_status()
            news = resp.json().get("news", [])[:limit]

            results: list[dict[str, Any]] = []
            for article in news:
                results.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "body": (article.get("description") or "")[:400],
                    "source": "currents",
                })
            return results

    except httpx.TimeoutException:
        logger.error("Currents news fetch timed out for query: %s", query)
        return []
    except Exception as exc:
        logger.error("Currents news fetch failed for query %s: %s", query, exc)
        return []
