"""Unit tests for PydanticAI tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent import AnalysisDeps
from services.tools import (
    _clean_text,
    _summarize_comments,
    clean_noise_tool,
    fetch_amazon_tool,
    fetch_devto_tool,
    fetch_guardian_tool,
    fetch_hackernews_tool,
    fetch_news_tool,
    fetch_reddit_tool,
    fetch_stackexchange_tool,
    fetch_youtube_tool,
    relevance_filter,
    search_web_tool,
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

# Create a mock RunContext with AnalysisDeps
def _mock_ctx(time_range: str = "week"):
    ctx = MagicMock()
    ctx.deps = AnalysisDeps(query="test query", time_range=time_range)
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
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            mock_fetch.return_value = posts
            mock_filter.return_value = (posts, 1.0)
            result = await fetch_reddit_tool(_mock_ctx(), "test")

        assert "Reddit Results" in result
        assert "Reddit Post" in result
        assert "Post content here" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_reddit", new_callable=AsyncMock) as mock, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            mock.return_value = []
            result = await fetch_reddit_tool(_mock_ctx(), "nothing")

        assert "No Reddit results" in result

    @pytest.mark.asyncio
    async def test_refetches_on_low_yield(self):
        """When yield < 50%, should refetch with 2x limit."""
        posts_batch1 = [
            {"title": f"Post {i}", "body": f"Content {i}", "url": f"http://r/{i}",
             "comments": [], "source": "reddit"}
            for i in range(15)  # week limit is 15
        ]
        posts_batch2 = [
            {"title": f"Post {i}", "body": f"Content {i}", "url": f"http://r/{i}",
             "comments": [], "source": "reddit"}
            for i in range(30)
        ]

        fetch_mock = AsyncMock(side_effect=[posts_batch1, posts_batch2])
        filter_mock = AsyncMock(side_effect=[
            (posts_batch1[:2], 0.4),   # First filter: 40% yield
            (posts_batch2[:6], 0.6),   # Second filter: 60% yield
        ])

        with patch("services.tools.fetch_reddit", fetch_mock), \
             patch("services.tools.relevance_filter", filter_mock), \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            await fetch_reddit_tool(_mock_ctx(), "test")

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
             patch("services.tools.relevance_filter", filter_mock), \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            result = await fetch_reddit_tool(_mock_ctx(), "test")

        assert fetch_mock.call_count == 1
        assert "Relevant Post" in result

    @pytest.mark.asyncio
    async def test_uses_cached_data(self):
        """When cache hit, should skip crawler entirely."""
        cached_posts = [
            {"title": "Cached Post", "body": "From cache", "url": "http://r/cached",
             "comments": [], "source": "reddit"}
        ]
        fetch_mock = AsyncMock()
        filter_mock = AsyncMock(return_value=(cached_posts, 1.0))

        with patch("services.tools.fetch_reddit", fetch_mock), \
             patch("services.tools.relevance_filter", filter_mock), \
             patch("services.tools.get_cached_fetch", return_value=cached_posts), \
             patch("services.tools.set_cached_fetch"):
            result = await fetch_reddit_tool(_mock_ctx(), "test")

        # Crawler should NOT have been called
        fetch_mock.assert_not_called()
        assert "Cached Post" in result


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
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            mock_fetch.return_value = videos
            mock_filter.return_value = (videos, 1.0)
            result = await fetch_youtube_tool(_mock_ctx(), "test")

        assert "YouTube Results" in result
        assert "YT Video" in result
        assert "TestChan" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_youtube", new_callable=AsyncMock) as mock, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
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
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            mock_fetch.return_value = items
            mock_filter.return_value = (items, 1.0)
            result = await fetch_amazon_tool(_mock_ctx(), "test")

        assert "Amazon Results" in result
        assert "Great product" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_amazon", new_callable=AsyncMock) as mock, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
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

    @pytest.mark.asyncio
    async def test_verdict_count_mismatch_fails_open(self):
        """When LLM returns fewer verdicts than items, fail open — return all items."""
        items = [
            {"title": "Post 1", "body": "Content 1"},
            {"title": "Post 2", "body": "Content 2"},
            {"title": "Post 3", "body": "Content 3"},
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # Only 2 verdicts for 3 items — mismatch
        mock_response.choices[0].message.content = "[true, false]"

        with patch("services.tools._openai_client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            relevant, yield_ratio = await relevance_filter("test", items, "reddit")

        # Should fail open: return all 3 items with yield 1.0
        assert len(relevant) == 3
        assert yield_ratio == 1.0


# ---------------------------------------------------------------------------
# _clean_text branch coverage
# ---------------------------------------------------------------------------


class TestCleanText:
    def test_amazon_nav_removed(self):
        """Amazon-specific nav boilerplate lines should be stripped."""
        text = "Back to top\nReal content here\n© 2024 Amazon.com, Inc."
        result = _clean_text(text, source="amazon")
        assert "Real content here" in result
        assert "Back to top" not in result
        assert "© 2024" not in result

    def test_reddit_removed_filtered(self):
        """[removed] lines for reddit source should be dropped."""
        text = "Good comment\n[removed]\nAnother good line"
        result = _clean_text(text, source="reddit")
        assert "Good comment" in result
        assert "Another good line" in result
        assert "[removed]" not in result

    def test_short_non_header_line_filtered(self):
        """Lines shorter than 5 chars that don't start with # should be dropped."""
        text = "Normal line with content\nhi\nAnother normal line"
        result = _clean_text(text, source="reddit")
        assert "Normal line with content" in result
        assert "Another normal line" in result
        # "hi" is 2 chars, no #, should be removed
        lines = result.split("\n")
        assert "hi" not in lines

    def test_short_header_line_preserved(self):
        """Short lines that start with # (markdown headers) should be kept."""
        text = "# Hi\nSome content below"
        result = _clean_text(text, source="reddit")
        assert "# Hi" in result

    def test_empty_input_returns_empty(self):
        assert _clean_text("") == ""


# ---------------------------------------------------------------------------
# Additional branch coverage for existing tool classes
# ---------------------------------------------------------------------------


class TestFetchRedditToolBranches:
    @pytest.mark.asyncio
    async def test_no_sections_after_formatting_returns_message(self):
        """Posts with no body and no comments produce no sections → specific message."""
        posts = [
            {
                "title": "Empty Post",
                "body": "",
                "comments": [],
                "url": "https://reddit.com/r/test/1",
                "source": "reddit",
            }
        ]
        with patch("services.tools.fetch_reddit", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            mock_fetch.return_value = posts
            mock_filter.return_value = (posts, 1.0)
            result = await fetch_reddit_tool(_mock_ctx(), "test")

        assert "No meaningful Reddit results" in result


class TestFetchAmazonToolBranches:
    @pytest.mark.asyncio
    async def test_runtime_error_returns_error_message(self):
        """When fetch_amazon raises RuntimeError, tool returns [ERROR] message."""
        with patch("services.tools.fetch_amazon", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.get_cached_fetch", return_value=None):
            mock_fetch.side_effect = RuntimeError("Crawl4AI failed")
            result = await fetch_amazon_tool(_mock_ctx(), "test product")

        assert "[ERROR]" in result
        assert "test product" in result

    @pytest.mark.asyncio
    async def test_no_relevant_results_message(self):
        """When relevance filter returns empty, returns specific no-relevant message."""
        items = [
            {"title": "Unrelated item", "content": "Not about query", "source": "amazon"}
        ]
        with patch("services.tools.fetch_amazon", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            mock_fetch.return_value = items
            mock_filter.return_value = ([], 0.0)
            result = await fetch_amazon_tool(_mock_ctx(), "specific product")

        assert "No relevant Amazon results" in result


# ---------------------------------------------------------------------------
# New tool tests: fetch_hackernews_tool
# ---------------------------------------------------------------------------


class TestFetchHackernewsTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        items = [
            {
                "title": "HN Story",
                "url": "https://news.ycombinator.com/item?id=1",
                "body": "Discussion about the story",
                "score": 100,
                "comments": [{"author": "hacker", "body": "Interesting!", "score": 10, "replies": []}],
            }
        ]
        with patch("services.tools.fetch_hackernews", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = (items, 1.0)
            result = await fetch_hackernews_tool(_mock_ctx(), "test")

        assert "Hacker News Results" in result
        assert "HN Story" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_hackernews", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            result = await fetch_hackernews_tool(_mock_ctx(), "nothing")

        assert "No Hacker News results" in result

    @pytest.mark.asyncio
    async def test_returns_no_relevant_message(self):
        items = [{"title": "Story", "url": "http://x", "body": "", "score": 0, "comments": []}]
        with patch("services.tools.fetch_hackernews", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = ([], 0.0)
            result = await fetch_hackernews_tool(_mock_ctx(), "test")

        assert "No relevant Hacker News results" in result

    @pytest.mark.asyncio
    async def test_score_in_output(self):
        items = [
            {"title": "Top Story", "url": "https://hn.com/1", "body": "Body text", "score": 999, "comments": []}
        ]
        with patch("services.tools.fetch_hackernews", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = (items, 1.0)
            result = await fetch_hackernews_tool(_mock_ctx(), "top")

        assert "999" in result


# ---------------------------------------------------------------------------
# New tool tests: fetch_devto_tool
# ---------------------------------------------------------------------------


class TestFetchDevtoTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        items = [
            {
                "title": "Dev.to Article",
                "url": "https://dev.to/user/article",
                "body": "Article body content here",
                "score": 50,
                "comments": [],
            }
        ]
        with patch("services.tools.fetch_devto", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = (items, 1.0)
            result = await fetch_devto_tool(_mock_ctx(), "python")

        assert "Dev.to Results" in result
        assert "Dev.to Article" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_devto", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            result = await fetch_devto_tool(_mock_ctx(), "nothing")

        assert "No Dev.to results" in result

    @pytest.mark.asyncio
    async def test_returns_no_relevant_message(self):
        items = [{"title": "Unrelated", "url": "http://x", "body": "off topic", "score": 0, "comments": []}]
        with patch("services.tools.fetch_devto", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = ([], 0.0)
            result = await fetch_devto_tool(_mock_ctx(), "specific tech")

        assert "No relevant Dev.to results" in result

    @pytest.mark.asyncio
    async def test_reactions_in_output(self):
        items = [
            {"title": "Popular Post", "url": "https://dev.to/1", "body": "Content", "score": 123, "comments": []}
        ]
        with patch("services.tools.fetch_devto", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = (items, 1.0)
            result = await fetch_devto_tool(_mock_ctx(), "popular")

        assert "123" in result
        assert "reactions" in result


# ---------------------------------------------------------------------------
# New tool tests: fetch_stackexchange_tool
# ---------------------------------------------------------------------------


class TestFetchStackexchangeTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        items = [
            {
                "title": "How to use Python asyncio?",
                "url": "https://stackoverflow.com/q/1",
                "body": "Use asyncio.run() for the main entry point.",
                "score": 42,
            }
        ]
        with patch("services.tools.fetch_stackexchange", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = (items, 1.0)
            result = await fetch_stackexchange_tool(_mock_ctx(), "asyncio")

        assert "Stack Overflow Results" in result
        assert "How to use Python asyncio?" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_stackexchange", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            result = await fetch_stackexchange_tool(_mock_ctx(), "nothing")

        assert "No Stack Overflow results" in result

    @pytest.mark.asyncio
    async def test_returns_no_relevant_message(self):
        items = [{"title": "Off-topic Q", "url": "http://x", "body": "unrelated", "score": 1}]
        with patch("services.tools.fetch_stackexchange", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = ([], 0.0)
            result = await fetch_stackexchange_tool(_mock_ctx(), "specific topic")

        assert "No relevant Stack Overflow results" in result

    @pytest.mark.asyncio
    async def test_score_in_output(self):
        items = [
            {"title": "Best answer question", "url": "https://so.com/q/2", "body": "Answer text", "score": 77}
        ]
        with patch("services.tools.fetch_stackexchange", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            mock_filter.return_value = (items, 1.0)
            result = await fetch_stackexchange_tool(_mock_ctx(), "best answer")

        assert "77" in result
        assert "score" in result


# ---------------------------------------------------------------------------
# New tool tests: fetch_guardian_tool (no relevance_filter step)
# ---------------------------------------------------------------------------


class TestFetchGuardianTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        items = [
            {
                "title": "Climate Change Update",
                "url": "https://theguardian.com/environment/1",
                "body": "Scientists report record temperatures across the globe.",
            }
        ]
        with patch("services.tools.fetch_guardian", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            result = await fetch_guardian_tool(_mock_ctx(), "climate")

        assert "The Guardian Results" in result
        assert "Climate Change Update" in result
        assert "Scientists report" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_guardian", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            result = await fetch_guardian_tool(_mock_ctx(), "nothing")

        assert "No Guardian results" in result

    @pytest.mark.asyncio
    async def test_multiple_articles_in_output(self):
        items = [
            {"title": "Article One", "url": "https://theguardian.com/1", "body": "Body one."},
            {"title": "Article Two", "url": "https://theguardian.com/2", "body": "Body two."},
        ]
        with patch("services.tools.fetch_guardian", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            result = await fetch_guardian_tool(_mock_ctx(), "news")

        assert "Article One" in result
        assert "Article Two" in result
        assert "2 articles" in result

    @pytest.mark.asyncio
    async def test_no_relevance_filter_called(self):
        """Guardian tool skips relevance filtering — verify relevance_filter not called."""
        items = [{"title": "Story", "url": "http://guardian.com/1", "body": "content"}]
        with patch("services.tools.fetch_guardian", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter:
            mock_fetch.return_value = items
            await fetch_guardian_tool(_mock_ctx(), "test")

        mock_filter.assert_not_called()


# ---------------------------------------------------------------------------
# New tool tests: fetch_news_tool
# ---------------------------------------------------------------------------


class TestFetchNewsTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        items = [
            {
                "title": "Breaking News",
                "url": "https://bbc.com/news/1",
                "body": "Major event occurred today.",
                "source": "BBC",
            }
        ]
        with patch("services.tools.fetch_news_rss", new_callable=AsyncMock) as mock_rss, \
             patch("services.tools.fetch_currents_news", new_callable=AsyncMock) as mock_currents:
            mock_rss.return_value = items
            mock_currents.return_value = []
            result = await fetch_news_tool(_mock_ctx(), "breaking news")

        assert "News Results" in result
        assert "Breaking News" in result
        assert "BBC" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_news_rss", new_callable=AsyncMock) as mock_rss, \
             patch("services.tools.fetch_currents_news", new_callable=AsyncMock) as mock_currents:
            mock_rss.return_value = []
            mock_currents.return_value = []
            result = await fetch_news_tool(_mock_ctx(), "nothing")

        assert "No news results" in result

    @pytest.mark.asyncio
    async def test_supplements_with_currents_when_rss_is_sparse(self):
        """When RSS returns fewer than 5 items, Currents API is called to supplement."""
        rss_items = [
            {"title": f"RSS Story {i}", "url": f"http://bbc.com/{i}", "body": "text", "source": "bbc"}
            for i in range(3)
        ]
        currents_items = [
            {"title": "Currents Story", "url": "http://currents.com/1", "body": "more news", "source": "currents"}
        ]
        with patch("services.tools.fetch_news_rss", new_callable=AsyncMock) as mock_rss, \
             patch("services.tools.fetch_currents_news", new_callable=AsyncMock) as mock_currents:
            mock_rss.return_value = rss_items
            mock_currents.return_value = currents_items
            result = await fetch_news_tool(_mock_ctx(), "world news")

        mock_currents.assert_called_once()
        assert "Currents Story" in result

    @pytest.mark.asyncio
    async def test_skips_currents_when_rss_is_full(self):
        """When RSS returns 5+ items, Currents API should NOT be called."""
        rss_items = [
            {"title": f"RSS Story {i}", "url": f"http://bbc.com/{i}", "body": "text", "source": "bbc"}
            for i in range(6)
        ]
        with patch("services.tools.fetch_news_rss", new_callable=AsyncMock) as mock_rss, \
             patch("services.tools.fetch_currents_news", new_callable=AsyncMock) as mock_currents:
            mock_rss.return_value = rss_items
            mock_currents.return_value = []
            result = await fetch_news_tool(_mock_ctx(), "world")

        mock_currents.assert_not_called()
        assert "6 articles" in result


# ---------------------------------------------------------------------------
# New tool tests: search_web_tool
# ---------------------------------------------------------------------------


class TestSearchWebTool:
    @pytest.mark.asyncio
    async def test_returns_formatted_text(self):
        items = [
            {
                "title": "Web Result",
                "url": "https://example.com/page",
                "body": "Relevant web page content.",
            }
        ]
        with patch("services.tools.fetch_tavily", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            result = await search_web_tool(_mock_ctx(), "niche topic")

        assert "Web Search Results" in result
        assert "Web Result" in result
        assert "Relevant web page content" in result

    @pytest.mark.asyncio
    async def test_returns_no_results_message(self):
        with patch("services.tools.fetch_tavily", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            result = await search_web_tool(_mock_ctx(), "nothing")

        assert "No web search results" in result

    @pytest.mark.asyncio
    async def test_multiple_results_in_output(self):
        items = [
            {"title": f"Result {i}", "url": f"https://example.com/{i}", "body": f"Content {i}"}
            for i in range(3)
        ]
        with patch("services.tools.fetch_tavily", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            result = await search_web_tool(_mock_ctx(), "multi")

        assert "3 results" in result
        assert "Result 0" in result
        assert "Result 2" in result


# ---------------------------------------------------------------------------
# Additional branch coverage: YouTube refetch + no-relevant, Reddit no-relevant
# ---------------------------------------------------------------------------


class TestFetchYoutubeToolBranches:
    @pytest.mark.asyncio
    async def test_refetches_on_low_yield(self):
        """When YouTube yield < 50%, should refetch with 2x limit."""
        # week limit is 15 — batch1 must be exactly 15 to satisfy len(videos) >= initial_limit
        initial_limit = 15
        videos_batch1 = [
            {"title": f"Video {i}", "channel": "Chan", "url": f"http://yt/{i}",
             "description": "desc", "comments": [], "source": "youtube"}
            for i in range(initial_limit)
        ]
        videos_batch2 = [
            {"title": f"Video {i}", "channel": "Chan", "url": f"http://yt/{i}",
             "description": "desc", "comments": [], "source": "youtube"}
            for i in range(initial_limit * 2)
        ]

        fetch_mock = AsyncMock(side_effect=[videos_batch1, videos_batch2])
        filter_mock = AsyncMock(side_effect=[
            (videos_batch1[:3], 0.2),    # First: 20% yield — triggers refetch
            (videos_batch2[:6], 0.6),    # Second: 60% yield
        ])

        with patch("services.tools.fetch_youtube", fetch_mock), \
             patch("services.tools.relevance_filter", filter_mock), \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            await fetch_youtube_tool(_mock_ctx(), "test")

        assert fetch_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_no_relevant_message(self):
        """When relevance filter returns empty after filtering, returns no-relevant message."""
        videos = [
            {"title": "Unrelated Video", "channel": "Chan", "url": "http://yt/1",
             "description": "off topic", "comments": [], "source": "youtube"}
        ]
        with patch("services.tools.fetch_youtube", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            mock_fetch.return_value = videos
            mock_filter.return_value = ([], 0.0)
            result = await fetch_youtube_tool(_mock_ctx(), "specific query")

        assert "No relevant YouTube results" in result


class TestFetchRedditToolNoRelevant:
    @pytest.mark.asyncio
    async def test_returns_no_relevant_message(self):
        """When relevance filter returns empty, returns no-relevant message."""
        posts = [
            {"title": "Unrelated Post", "body": "off topic", "comments": [],
             "url": "http://r/1", "source": "reddit"}
        ]
        with patch("services.tools.fetch_reddit", new_callable=AsyncMock) as mock_fetch, \
             patch("services.tools.relevance_filter", new_callable=AsyncMock) as mock_filter, \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            mock_fetch.return_value = posts
            mock_filter.return_value = ([], 0.0)
            result = await fetch_reddit_tool(_mock_ctx(), "specific query")

        assert "No relevant Reddit results" in result


# ---------------------------------------------------------------------------
# Additional branch coverage: _clean_text consecutive blank lines
# ---------------------------------------------------------------------------


class TestCleanTextBlanks:
    def test_consecutive_blank_lines_collapsed(self):
        """Multiple blank lines in a row should collapse to one blank line."""
        text = "Line 1\n\n\n\nLine 2"
        result = _clean_text(text, source="reddit")
        # Should not have two consecutive blank lines
        assert "\n\n\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result


# ---------------------------------------------------------------------------
# Additional branch coverage: _summarize_comments skips deleted
# ---------------------------------------------------------------------------


class TestSummarizeCommentsDeleted:
    def test_skips_deleted_body(self):
        """Comments with [deleted] or [removed] body are skipped."""
        comments = [
            {"author": "user1", "body": "[deleted]", "score": 5, "replies": []},
            {"author": "user2", "body": "[removed]", "score": 3, "replies": []},
            {"author": "user3", "body": "Valid comment", "score": 10, "replies": []},
        ]
        result = _summarize_comments(comments)
        assert "user3" in result
        assert "Valid comment" in result
        assert "[deleted]" not in result
        assert "[removed]" not in result
        # user1 and user2 should not appear (their bodies are deleted)
        assert "user1" not in result
        assert "user2" not in result


# ---------------------------------------------------------------------------
# Additional branch coverage: Amazon refetch RuntimeError
# ---------------------------------------------------------------------------


class TestFetchAmazonToolRefetchError:
    @pytest.mark.asyncio
    async def test_runtime_error_on_refetch_is_handled(self):
        """RuntimeError on the refetch attempt is caught and tool continues gracefully."""
        # initial_limit for "week" — make results list length >= initial_limit to trigger refetch
        # We need len(results) >= initial_max and yield < 0.5
        # Use a large list to ensure the refetch condition triggers
        many_items = [
            {"title": f"Product {i}", "content": f"Content {i}", "source": "amazon"}
            for i in range(20)
        ]

        fetch_mock = AsyncMock(side_effect=[
            many_items,        # first call succeeds
            RuntimeError("Crawl4AI crashed on refetch"),  # refetch fails
        ])
        filter_mock = AsyncMock(return_value=([], 0.0))  # yield = 0%, triggers refetch

        with patch("services.tools.fetch_amazon", fetch_mock), \
             patch("services.tools.relevance_filter", filter_mock), \
             patch("services.tools.get_cached_fetch", return_value=None), \
             patch("services.tools.set_cached_fetch"):
            result = await fetch_amazon_tool(_mock_ctx(), "test product")

        # After refetch error, no relevant results — should return no-relevant message
        assert "No relevant Amazon results" in result
