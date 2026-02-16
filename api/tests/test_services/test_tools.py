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
    relevance_filter,
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
        with patch("services.tools.fetch_reddit", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = posts
            mock_filter.return_value = (posts, 1.0)
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

    @pytest.mark.asyncio
    async def test_refetches_on_low_yield(self):
        """When yield < 50%, should refetch with 2x limit."""
        posts_batch1 = [
            {"title": f"Post {i}", "body": f"Content {i}", "url": f"http://r/{i}",
             "comments": [], "source": "reddit"}
            for i in range(5)
        ]
        posts_batch2 = [
            {"title": f"Post {i}", "body": f"Content {i}", "url": f"http://r/{i}",
             "comments": [], "source": "reddit"}
            for i in range(10)
        ]

        fetch_mock = AsyncMock(side_effect=[posts_batch1, posts_batch2])
        filter_mock = AsyncMock(side_effect=[
            (posts_batch1[:2], 0.4),   # First filter: 40% yield
            (posts_batch2[:6], 0.6),   # Second filter: 60% yield
        ])

        with patch("services.tools.fetch_reddit", fetch_mock), \
             patch("services.tools.relevance_filter", filter_mock):
            result = await fetch_reddit_tool(_mock_ctx(), "test")

        assert fetch_mock.call_count == 2
        assert filter_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_no_refetch_on_good_yield(self):
        """When yield >= 50%, should NOT refetch."""
        posts = [
            {"title": "Relevant Post", "body": "Good content", "url": "http://r/1",
             "comments": [{"author": "u1", "body": "nice", "score": 5, "replies": []}],
             "source": "reddit"}
        ]
        fetch_mock = AsyncMock(return_value=posts)
        filter_mock = AsyncMock(return_value=(posts, 1.0))

        with patch("services.tools.fetch_reddit", fetch_mock), \
             patch("services.tools.relevance_filter", filter_mock):
            result = await fetch_reddit_tool(_mock_ctx(), "test")

        assert fetch_mock.call_count == 1
        assert "Relevant Post" in result


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
        with patch("services.tools.fetch_youtube", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = videos
            mock_filter.return_value = (videos, 1.0)
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
        with patch("services.tools.fetch_amazon", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = (items, 1.0)
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


# ---------------------------------------------------------------------------
# Relevance filter tests
# ---------------------------------------------------------------------------


class TestRelevanceFilter:
    @pytest.mark.asyncio
    async def test_filters_irrelevant_items(self):
        """Filter should remove items the LLM marks as irrelevant."""
        items = [
            {"title": "Plaud AI Note Review", "body": "Great device for meetings"},
            {"title": "Best AI tools 2026", "body": "A list of random AI tools"},
            {"title": "Plaud AI vs Otter", "body": "Comparison of transcription devices"},
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "[true, false, true]"

        with patch("services.tools._openai_client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            relevant, yield_ratio = await relevance_filter("plaud ai", items, "reddit")

        assert len(relevant) == 2
        assert relevant[0]["title"] == "Plaud AI Note Review"
        assert relevant[1]["title"] == "Plaud AI vs Otter"
        assert yield_ratio == pytest.approx(2 / 3)

    @pytest.mark.asyncio
    async def test_returns_all_on_api_failure(self):
        """On OpenAI API failure, fail open — return all items with yield 1.0."""
        items = [
            {"title": "Post 1", "body": "Content 1"},
            {"title": "Post 2", "body": "Content 2"},
        ]
        with patch("services.tools._openai_client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API error")
            )
            relevant, yield_ratio = await relevance_filter("test", items, "reddit")

        assert len(relevant) == 2
        assert yield_ratio == 1.0

    @pytest.mark.asyncio
    async def test_empty_items(self):
        """Empty input returns empty output with yield 1.0."""
        relevant, yield_ratio = await relevance_filter("test", [], "reddit")
        assert relevant == []
        assert yield_ratio == 1.0

    @pytest.mark.asyncio
    async def test_all_relevant(self):
        """When all items are relevant, yield is 1.0."""
        items = [
            {"title": "Plaud AI Review", "body": "Amazing device"},
            {"title": "Plaud Note hands-on", "body": "My experience"},
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "[true, true]"

        with patch("services.tools._openai_client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            relevant, yield_ratio = await relevance_filter("plaud ai", items, "reddit")

        assert len(relevant) == 2
        assert yield_ratio == 1.0

    @pytest.mark.asyncio
    async def test_uses_content_field_for_amazon(self):
        """Amazon items use 'content' instead of 'body' — should still work."""
        items = [
            {"title": "PLAUD AI Note", "content": "Product page content here"},
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "[true]"

        with patch("services.tools._openai_client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            relevant, yield_ratio = await relevance_filter("plaud ai", items, "amazon")

        assert len(relevant) == 1
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_malformed_llm_response(self):
        """If LLM returns non-JSON, fail open."""
        items = [{"title": "Post", "body": "Content"}]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json"

        with patch("services.tools._openai_client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            relevant, yield_ratio = await relevance_filter("test", items, "reddit")

        assert len(relevant) == 1
        assert yield_ratio == 1.0
