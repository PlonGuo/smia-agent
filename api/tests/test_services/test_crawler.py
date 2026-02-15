"""Unit tests for crawler service (Reddit / YouTube / Amazon)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.crawler import (
    _crawl4ai_fetch,
    _fetch_yt_comments,
    _firecrawl_fetch,
    fetch_amazon,
    fetch_reddit,
    fetch_youtube,
)


# ---------------------------------------------------------------------------
# Reddit (YARS) tests
# ---------------------------------------------------------------------------


class TestFetchReddit:
    """Tests for fetch_reddit()."""

    @pytest.mark.asyncio
    async def test_returns_posts_on_success(self):
        mock_miner = MagicMock()
        mock_miner.search_reddit.return_value = [
            {
                "title": "Test Post",
                "link": "https://www.reddit.com/r/test/comments/abc/test_post/",
                "permalink": "/r/test/comments/abc/test_post/",
                "description": "A test post",
            }
        ]
        mock_miner.scrape_post_details.return_value = {
            "title": "Test Post",
            "body": "Post body text",
            "comments": [{"author": "user1", "body": "Great!", "score": 5, "replies": []}],
        }

        with patch("services.crawler._get_yars", return_value=mock_miner):
            posts = await fetch_reddit("test query", limit=1)

        assert len(posts) == 1
        assert posts[0]["title"] == "Test Post"
        assert posts[0]["body"] == "Post body text"
        assert posts[0]["source"] == "reddit"
        assert len(posts[0]["comments"]) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(self):
        mock_miner = MagicMock()
        mock_miner.search_reddit.return_value = []

        with patch("services.crawler._get_yars", return_value=mock_miner):
            posts = await fetch_reddit("no results query")

        assert posts == []

    @pytest.mark.asyncio
    async def test_falls_back_on_failed_post_details(self):
        mock_miner = MagicMock()
        mock_miner.search_reddit.return_value = [
            {"title": "P1", "link": "u1", "permalink": "/r/t/1/", "description": ""},
            {"title": "P2", "link": "u2", "permalink": "/r/t/2/", "description": "d2"},
        ]
        # First post scrape succeeds, second returns None (falls back to search data)
        mock_miner.scrape_post_details.side_effect = [
            {"title": "P1", "body": "b1", "comments": []},
            None,
        ]

        with patch("services.crawler._get_yars", return_value=mock_miner):
            posts = await fetch_reddit("mixed", limit=2)

        assert len(posts) == 2
        assert posts[0]["title"] == "P1"
        assert posts[0]["body"] == "b1"
        # Second post uses search result data as fallback
        assert posts[1]["title"] == "P2"
        assert posts[1]["body"] == "d2"
        assert posts[1]["comments"] == []

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        with patch("services.crawler._get_yars", side_effect=RuntimeError("boom")):
            posts = await fetch_reddit("fail")

        assert posts == []


# ---------------------------------------------------------------------------
# YouTube tests
# ---------------------------------------------------------------------------


class TestFetchYoutube:
    """Tests for fetch_youtube()."""

    @pytest.mark.asyncio
    async def test_returns_videos_with_comments(self):
        search_json = {
            "items": [
                {
                    "id": {"videoId": "vid123"},
                    "snippet": {
                        "title": "Test Video",
                        "description": "A test video",
                        "channelTitle": "TestChannel",
                        "publishedAt": "2025-01-01T00:00:00Z",
                    },
                }
            ]
        }
        comments_json = {
            "items": [
                {
                    "snippet": {
                        "topLevelComment": {
                            "snippet": {
                                "authorDisplayName": "commenter",
                                "textDisplay": "Nice video!",
                                "likeCount": 10,
                                "publishedAt": "2025-01-02T00:00:00Z",
                            }
                        }
                    }
                }
            ]
        }

        with patch("services.crawler.settings") as mock_settings:
            mock_settings.youtube_api_key = "test-key"

            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

                # search response
                search_resp = MagicMock()
                search_resp.json.return_value = search_json
                search_resp.raise_for_status = MagicMock()

                # comments response
                comments_resp = MagicMock()
                comments_resp.json.return_value = comments_json
                comments_resp.raise_for_status = MagicMock()

                mock_client.get = AsyncMock(side_effect=[search_resp, comments_resp])

                videos = await fetch_youtube("test", max_videos=1)

        assert len(videos) == 1
        assert videos[0]["title"] == "Test Video"
        assert videos[0]["video_id"] == "vid123"
        assert videos[0]["source"] == "youtube"
        assert len(videos[0]["comments"]) == 1
        assert videos[0]["comments"][0]["text"] == "Nice video!"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_api_key(self):
        with patch("services.crawler.settings") as mock_settings:
            mock_settings.youtube_api_key = ""
            videos = await fetch_youtube("test")
        assert videos == []

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self):
        with patch("services.crawler.settings") as mock_settings:
            mock_settings.youtube_api_key = "test-key"

            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

                mock_client.get = AsyncMock(
                    side_effect=httpx.HTTPStatusError(
                        "403 Forbidden",
                        request=MagicMock(),
                        response=MagicMock(status_code=403),
                    )
                )

                videos = await fetch_youtube("test")

        assert videos == []


# ---------------------------------------------------------------------------
# YouTube comments helper
# ---------------------------------------------------------------------------


class TestFetchYtComments:
    """Tests for _fetch_yt_comments()."""

    @pytest.mark.asyncio
    async def test_returns_comments(self):
        resp = MagicMock()
        resp.json.return_value = {
            "items": [
                {
                    "snippet": {
                        "topLevelComment": {
                            "snippet": {
                                "authorDisplayName": "User",
                                "textDisplay": "Hello",
                                "likeCount": 3,
                                "publishedAt": "2025-01-01T00:00:00Z",
                            }
                        }
                    }
                }
            ]
        }
        resp.raise_for_status = MagicMock()

        client = AsyncMock()
        client.get = AsyncMock(return_value=resp)

        comments = await _fetch_yt_comments(client, "vid1", "key", 10)
        assert len(comments) == 1
        assert comments[0]["author"] == "User"
        assert comments[0]["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        client = AsyncMock()
        client.get = AsyncMock(side_effect=Exception("network error"))

        comments = await _fetch_yt_comments(client, "vid1", "key", 10)
        assert comments == []


# ---------------------------------------------------------------------------
# Amazon / Crawl4AI / Firecrawl tests
# ---------------------------------------------------------------------------


class TestFetchAmazon:
    """Tests for fetch_amazon()."""

    @pytest.mark.asyncio
    async def test_returns_search_content_when_no_product_urls(self):
        """When search page has no product URLs, returns trimmed search content."""
        with patch("services.crawler._crawl4ai_fetch", new_callable=AsyncMock) as mock_c4a:
            mock_c4a.return_value = "# Amazon Product\nGreat product reviews here!"
            with patch("services.crawler._firecrawl_fetch", new_callable=AsyncMock) as mock_fc:
                result = await fetch_amazon("test product")

        assert len(result) == 1
        assert result[0]["source"] == "amazon"
        assert "test product" in result[0]["title"]
        # Crawl4AI was called once for the search page
        mock_c4a.assert_called_once()
        mock_fc.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_firecrawl(self):
        with patch("services.crawler._crawl4ai_fetch", new_callable=AsyncMock) as mock_c4a:
            mock_c4a.return_value = None
            with patch("services.crawler._firecrawl_fetch", new_callable=AsyncMock) as mock_fc:
                mock_fc.return_value = "# Firecrawl result"
                result = await fetch_amazon("test product")

        assert len(result) == 1
        assert result[0]["source"] == "amazon"

    @pytest.mark.asyncio
    async def test_raises_when_both_fail(self):
        with patch("services.crawler._crawl4ai_fetch", new_callable=AsyncMock) as mock_c4a:
            mock_c4a.return_value = None
            with patch("services.crawler._firecrawl_fetch", new_callable=AsyncMock) as mock_fc:
                mock_fc.return_value = None
                with pytest.raises(RuntimeError, match="Amazon crawling failed"):
                    await fetch_amazon("test product")

    @pytest.mark.asyncio
    async def test_scrapes_product_pages_when_urls_found(self):
        """When search results contain product URLs, scrapes individual pages."""
        search_content = (
            "Results for test\n"
            "https://www.amazon.com/Test-Product/dp/B0TSTPRD01 - Product 1\n"
        )

        async def mock_crawl4ai(url):
            if "/s?k=" in url:
                return search_content
            if "B0TSTPRD01" in url:
                return "### Customers say\nGreat product with many features.\n### Top reviews from the United States\nAmazing quality!"
            return None

        with patch("services.crawler._crawl4ai_fetch", new_callable=AsyncMock, side_effect=mock_crawl4ai):
            with patch("services.crawler._firecrawl_fetch", new_callable=AsyncMock, return_value=None):
                result = await fetch_amazon("test product", max_products=1)

        assert len(result) == 1
        assert "Customers say" in result[0]["content"]


class TestCrawl4aiFetch:
    """Tests for _crawl4ai_fetch()."""

    @pytest.mark.asyncio
    async def test_returns_markdown_on_success(self):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Page Content"

        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.arun = AsyncMock(return_value=mock_result)
        mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
        mock_crawler_instance.__aexit__ = AsyncMock(return_value=False)

        mock_crawl4ai = MagicMock()
        mock_crawl4ai.AsyncWebCrawler = MagicMock(return_value=mock_crawler_instance)
        mock_crawl4ai.BrowserConfig = MagicMock()
        mock_crawl4ai.CrawlerRunConfig = MagicMock()

        with patch.dict("sys.modules", {"crawl4ai": mock_crawl4ai}):
            result = await _crawl4ai_fetch("https://example.com")

        assert result == "# Page Content"

    @pytest.mark.asyncio
    async def test_returns_none_on_failed_result(self):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.markdown = None

        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.arun = AsyncMock(return_value=mock_result)
        mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
        mock_crawler_instance.__aexit__ = AsyncMock(return_value=False)

        mock_crawl4ai = MagicMock()
        mock_crawl4ai.AsyncWebCrawler = MagicMock(return_value=mock_crawler_instance)
        mock_crawl4ai.BrowserConfig = MagicMock()
        mock_crawl4ai.CrawlerRunConfig = MagicMock()

        with patch.dict("sys.modules", {"crawl4ai": mock_crawl4ai}):
            result = await _crawl4ai_fetch("https://example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_import_error(self):
        """When crawl4ai is not installed, returns None."""
        original = sys.modules.get("crawl4ai")
        sys.modules["crawl4ai"] = None  # type: ignore[assignment]
        try:
            result = await _crawl4ai_fetch("https://example.com")
            assert result is None
        except (ImportError, TypeError):
            pass  # Also acceptable – ImportError propagation
        finally:
            if original is not None:
                sys.modules["crawl4ai"] = original
            else:
                sys.modules.pop("crawl4ai", None)


class TestFirecrawlFetch:
    """Tests for _firecrawl_fetch()."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_api_key(self):
        with patch("services.crawler.settings") as mock_settings:
            mock_settings.firecrawl_api_key = ""
            result = await _firecrawl_fetch("https://example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_markdown_on_success(self):
        mock_doc = MagicMock()
        mock_doc.markdown = "# Scraped content"

        mock_app = AsyncMock()
        mock_app.scrape_url = AsyncMock(return_value=mock_doc)

        with patch("services.crawler.settings") as mock_settings:
            mock_settings.firecrawl_api_key = "fc-test-key"
            with patch("firecrawl.AsyncFirecrawlApp", return_value=mock_app):
                result = await _firecrawl_fetch("https://example.com")

        assert result == "# Scraped content"

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        with patch("services.crawler.settings") as mock_settings:
            mock_settings.firecrawl_api_key = "fc-test-key"
            with patch(
                "firecrawl.AsyncFirecrawlApp",
                side_effect=Exception("connection error"),
            ):
                result = await _firecrawl_fetch("https://example.com")

        assert result is None


import sys
