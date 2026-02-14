"""Unit tests for PydanticAI tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.tools import (
    _summarize_comments,
    clean_noise_tool,
    fetch_amazon_tool,
    fetch_reddit_tool,
    fetch_youtube_tool,
)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestSummarizeComments:
    def test_basic_comments(self):
        comments = [
            {"author": "user1", "body": "Great post!", "score": 10, "replies": []},
            {"author": "user2", "text": "I agree", "likes": 5},
        ]
        result = _summarize_comments(comments)
        assert "user1" in result
        assert "Great post!" in result
        assert "user2" in result
        assert "I agree" in result

    def test_with_replies(self):
        comments = [
            {
                "author": "user1",
                "body": "Main comment",
                "score": 10,
                "replies": [
                    {"author": "replier", "body": "Reply text", "score": 3},
                ],
            },
        ]
        result = _summarize_comments(comments)
        assert "replier" in result
        assert "Reply text" in result

    def test_empty_comments(self):
        assert _summarize_comments([]) == ""

    def test_respects_max_comments(self):
        comments = [{"author": f"u{i}", "body": f"c{i}", "score": i} for i in range(20)]
        result = _summarize_comments(comments, max_comments=3)
        assert "u0" in result
        assert "u2" in result
        assert "u3" not in result


# ---------------------------------------------------------------------------
# Tool function tests (mocking crawlers)
# ---------------------------------------------------------------------------

# Create a mock RunContext
def _mock_ctx():
    ctx = MagicMock()
    ctx.deps = "test query"
    return ctx


class TestFetchRedditTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        posts = [
            {
                "title": "Reddit Post",
                "body": "Post content here",
                "comments": [{"author": "u1", "body": "nice", "score": 5, "replies": []}],
                "url": "https://reddit.com/r/test/1",
                "source": "reddit",
            }
        ]
        with patch("services.tools.fetch_reddit", new_callable=AsyncMock) as mock:
            mock.return_value = posts
            result = await fetch_reddit_tool(_mock_ctx(), "test")

        assert "Reddit Results" in result
        assert "Reddit Post" in result
        assert "Post content here" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_reddit", new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await fetch_reddit_tool(_mock_ctx(), "nothing")

        assert "No Reddit results" in result


class TestFetchYoutubeTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        videos = [
            {
                "title": "YT Video",
                "channel": "TestChan",
                "url": "https://youtube.com/watch?v=abc",
                "description": "A video",
                "comments": [{"author": "viewer", "text": "cool!", "likes": 3}],
                "source": "youtube",
            }
        ]
        with patch("services.tools.fetch_youtube", new_callable=AsyncMock) as mock:
            mock.return_value = videos
            result = await fetch_youtube_tool(_mock_ctx(), "test")

        assert "YouTube Results" in result
        assert "YT Video" in result
        assert "TestChan" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_youtube", new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await fetch_youtube_tool(_mock_ctx(), "nothing")

        assert "No YouTube results" in result


class TestFetchAmazonTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        items = [
            {
                "title": "Amazon results for: test",
                "content": "# Product\nGreat product with many reviews",
                "source": "amazon",
            }
        ]
        with patch("services.tools.fetch_amazon", new_callable=AsyncMock) as mock:
            mock.return_value = items
            result = await fetch_amazon_tool(_mock_ctx(), "test")

        assert "Amazon Results" in result
        assert "Great product" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_amazon", new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await fetch_amazon_tool(_mock_ctx(), "nothing")

        assert "No Amazon results" in result


class TestCleanNoiseTool:
    @pytest.mark.asyncio
    async def test_removes_noise(self):
        data = """# Product Review
Great product!
Subscribe to our newsletter
This is sponsored
Real user opinion here
[deleted]
Another good comment"""
        result = await clean_noise_tool(_mock_ctx(), data, "reddit")
        assert "Great product!" in result
        assert "Real user opinion" in result
        assert "Another good comment" in result
        assert "Subscribe to our newsletter" not in result
        assert "sponsored" not in result.lower().split("\n")[2] if len(result.split("\n")) > 2 else True
        assert "[deleted]" not in result

    @pytest.mark.asyncio
    async def test_preserves_headers(self):
        data = "# Title\n## Subtitle\nContent"
        result = await clean_noise_tool(_mock_ctx(), data, "reddit")
        assert "# Title" in result
        assert "## Subtitle" in result

    @pytest.mark.asyncio
    async def test_empty_input(self):
        result = await clean_noise_tool(_mock_ctx(), "", "reddit")
        assert result == ""

    @pytest.mark.asyncio
    async def test_preserves_blank_lines(self):
        data = "Line 1\n\nLine 2"
        result = await clean_noise_tool(_mock_ctx(), data, "reddit")
        assert "Line 1" in result
        assert "Line 2" in result
