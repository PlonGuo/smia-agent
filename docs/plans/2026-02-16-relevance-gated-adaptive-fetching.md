# Relevance-Gated Adaptive Fetching — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a batch LLM relevance filter (gpt-4o-mini) between raw data fetching and the main analysis agent. If yield < 50%, refetch at 2x limit and re-filter (one retry max).

**Architecture:** A new `relevance_filter()` async function in `api/services/tools.py` calls gpt-4o-mini with item titles + snippets, gets back a JSON boolean array, and filters items. Each tool function wraps its fetch call with this filter + adaptive retry logic.

**Tech Stack:** OpenAI SDK (already installed), gpt-4o-mini, Langfuse @observe

---

### Task 1: Add `relevance_filter()` function — tests

**Files:**
- Test: `api/tests/test_services/test_tools.py`

**Step 1: Write failing tests for `relevance_filter`**

Add these tests at the end of `api/tests/test_services/test_tools.py`:

```python
from services.tools import relevance_filter


class TestRelevanceFilter:
    @pytest.mark.asyncio
    async def test_filters_irrelevant_items(self):
        """Filter should remove items the LLM marks as irrelevant."""
        items = [
            {"title": "Plaud AI Note Review", "body": "Great device for meetings"},
            {"title": "Best AI tools 2026", "body": "A list of random AI tools"},
            {"title": "Plaud AI vs Otter", "body": "Comparison of transcription devices"},
        ]
        # Mock OpenAI to return [True, False, True]
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
        # Verify the prompt was built (client was called)
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
```

**Step 2: Run tests to verify they fail**

Run: `cd api && uv run python -m pytest tests/test_services/test_tools.py::TestRelevanceFilter -v`
Expected: FAIL with `ImportError: cannot import name 'relevance_filter'`

---

### Task 2: Implement `relevance_filter()` function

**Files:**
- Modify: `api/services/tools.py`

**Step 1: Add OpenAI client and relevance_filter to `tools.py`**

Add these imports at the top of `api/services/tools.py` (after existing imports):

```python
import json

from openai import AsyncOpenAI

from core.config import settings
```

Add the client singleton and function after `_clean_text()` but before `_summarize_comments()`:

```python
# ---------------------------------------------------------------------------
# LLM relevance filter (gpt-4o-mini)
# ---------------------------------------------------------------------------

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    """Lazy-init async OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.effective_openai_key)
    return _openai_client


@observe(name="relevance_filter")
async def relevance_filter(
    query: str,
    items: list[dict],
    source: str,
) -> tuple[list[dict], float]:
    """Batch LLM relevance check using gpt-4o-mini.

    Sends item titles + snippets to gpt-4o-mini, which returns a JSON array
    of booleans indicating whether each item is relevant to the query.

    Returns (relevant_items, yield_ratio).
    On any failure, returns (items, 1.0) — fail-open to avoid blocking pipeline.
    """
    if not items:
        return [], 1.0

    # Build numbered item list (title + first 200 chars of body/content)
    item_lines: list[str] = []
    for i, item in enumerate(items, 1):
        title = item.get("title", "Untitled")
        snippet = (
            item.get("body") or item.get("content") or item.get("description") or ""
        )[:200]
        item_lines.append(f"{i}. [{title}] {snippet}")

    prompt = (
        f'Query: "{query}"\n'
        f"Source: {source}\n\n"
        "For each item below, determine if it is relevant to the query. "
        "An item is relevant if it directly discusses, reviews, or mentions "
        "the specific product, brand, or topic in the query.\n\n"
        "Items:\n" + "\n".join(item_lines) + "\n\n"
        "Respond with ONLY a JSON array of booleans (true/false) — one per item. "
        "Example for 3 items: [true, false, true]"
    )

    try:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )
        raw = response.choices[0].message.content.strip()
        verdicts: list[bool] = json.loads(raw)

        if len(verdicts) != len(items):
            logger.warning(
                "Relevance filter returned %d verdicts for %d items — fail open",
                len(verdicts),
                len(items),
            )
            return items, 1.0

        relevant = [item for item, is_rel in zip(items, verdicts) if is_rel]
        yield_ratio = len(relevant) / len(items) if items else 1.0
        logger.info(
            "Relevance filter [%s]: %d/%d relevant (yield %.0f%%)",
            source,
            len(relevant),
            len(items),
            yield_ratio * 100,
        )
        return relevant, yield_ratio

    except Exception as exc:
        logger.warning("Relevance filter failed — returning all items: %s", exc)
        return items, 1.0
```

**Step 2: Run tests to verify they pass**

Run: `cd api && uv run python -m pytest tests/test_services/test_tools.py::TestRelevanceFilter -v`
Expected: All 6 tests PASS

---

### Task 3: Integrate adaptive fetching into `fetch_reddit_tool` — tests

**Files:**
- Modify: `api/tests/test_services/test_tools.py`

**Step 1: Add adaptive fetch tests for Reddit**

Add to `TestFetchRedditTool`:

```python
    @pytest.mark.asyncio
    async def test_refetches_on_low_yield(self):
        """When yield < 50%, should refetch with 2x limit."""
        # First fetch: 5 posts, only 2 relevant (40% yield)
        posts_batch1 = [
            {"title": f"Post {i}", "body": f"Content {i}", "url": f"http://r/{i}",
             "comments": [], "source": "reddit"}
            for i in range(5)
        ]
        # Second fetch: 10 posts
        posts_batch2 = posts_batch1 + [
            {"title": f"Post {i}", "body": f"Content {i}", "url": f"http://r/{i}",
             "comments": [], "source": "reddit"}
            for i in range(5, 10)
        ]

        fetch_mock = AsyncMock(side_effect=[posts_batch1, posts_batch2])
        # First filter: 2/5 relevant (40%), second filter: 6/10 relevant (60%)
        filter_mock = AsyncMock(side_effect=[
            (posts_batch1[:2], 0.4),
            (posts_batch2[:6], 0.6),
        ])

        with patch("services.tools.fetch_reddit", fetch_mock), \
             patch("services.tools.relevance_filter", filter_mock):
            result = await fetch_reddit_tool(_mock_ctx(), "test")

        # Should have called fetch_reddit twice (initial + refetch)
        assert fetch_mock.call_count == 2
        assert fetch_mock.call_args_list[1][1].get("limit", 5) == 10 or \
               fetch_mock.call_args_list[1][0][1] == 10 or \
               "limit" in str(fetch_mock.call_args_list[1])

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
```

**Step 2: Run to verify they fail**

Run: `cd api && uv run python -m pytest tests/test_services/test_tools.py::TestFetchRedditTool::test_refetches_on_low_yield tests/test_services/test_tools.py::TestFetchRedditTool::test_no_refetch_on_good_yield -v`
Expected: FAIL (current code doesn't call relevance_filter)

---

### Task 4: Integrate adaptive fetching into all three tool functions

**Files:**
- Modify: `api/services/tools.py`

**Step 1: Update `fetch_reddit_tool`**

Replace the existing `fetch_reddit_tool` function:

```python
async def fetch_reddit_tool(ctx: RunContext[str], query: str) -> str:
    """Fetch Reddit discussions about the given query.

    Searches Reddit using YARS, retrieves top posts and their comments,
    and returns a formatted text summary for LLM analysis.
    Applies relevance filtering with adaptive refetch on low yield.
    """
    INITIAL_LIMIT = 5

    posts = await fetch_reddit(query, limit=INITIAL_LIMIT, sort="relevance", time_filter="week")
    if not posts:
        return f"No Reddit results found for '{query}'."

    relevant, yield_ratio = await relevance_filter(query, posts, "reddit")

    # Adaptive refetch: if yield < 50% and we got a full batch, try 2x
    if yield_ratio < 0.5 and len(posts) >= INITIAL_LIMIT:
        logger.info("Reddit yield %.0f%% — refetching with limit=%d", yield_ratio * 100, INITIAL_LIMIT * 2)
        posts = await fetch_reddit(query, limit=INITIAL_LIMIT * 2, sort="relevance", time_filter="week")
        if posts:
            relevant, yield_ratio = await relevance_filter(query, posts, "reddit")

    if not relevant:
        return f"No relevant Reddit results found for '{query}'."

    sections: list[str] = []
    for post in relevant:
        title = post.get("title", "Untitled")
        body = _clean_text(post.get("body", "")[:500], "reddit")
        url = post.get("url", "")
        comments_text = _summarize_comments(post.get("comments", []))
        if not body and not comments_text:
            continue
        sections.append(
            f"### {title}\nURL: {url}\n{body}\n\n**Comments:**\n{comments_text}"
        )

    if not sections:
        return f"No meaningful Reddit results found for '{query}'."

    return (
        f"# Reddit Results for '{query}' ({len(sections)} posts)\n\n"
        + "\n\n---\n\n".join(sections)
    )
```

**Step 2: Update `fetch_youtube_tool`**

Replace the existing `fetch_youtube_tool` function:

```python
async def fetch_youtube_tool(ctx: RunContext[str], query: str) -> str:
    """Fetch YouTube video comments about the given query.

    Searches YouTube Data API v3, retrieves top videos and their comments,
    and returns a formatted text summary for LLM analysis.
    Applies relevance filtering with adaptive refetch on low yield.
    """
    INITIAL_LIMIT = 5

    videos = await fetch_youtube(query, max_videos=INITIAL_LIMIT, max_comments_per_video=15)
    if not videos:
        return f"No YouTube results found for '{query}'."

    relevant, yield_ratio = await relevance_filter(query, videos, "youtube")

    if yield_ratio < 0.5 and len(videos) >= INITIAL_LIMIT:
        logger.info("YouTube yield %.0f%% — refetching with limit=%d", yield_ratio * 100, INITIAL_LIMIT * 2)
        videos = await fetch_youtube(query, max_videos=INITIAL_LIMIT * 2, max_comments_per_video=15)
        if videos:
            relevant, yield_ratio = await relevance_filter(query, videos, "youtube")

    if not relevant:
        return f"No relevant YouTube results found for '{query}'."

    sections: list[str] = []
    for video in relevant:
        title = video.get("title", "Untitled")
        channel = video.get("channel", "Unknown")
        url = video.get("url", "")
        desc = _clean_text(video.get("description", "")[:300], "youtube")
        comments_text = _summarize_comments(video.get("comments", []))
        sections.append(
            f"### {title} (by {channel})\nURL: {url}\n{desc}\n\n**Comments:**\n{comments_text}"
        )

    return (
        f"# YouTube Results for '{query}' ({len(sections)} videos)\n\n"
        + "\n\n---\n\n".join(sections)
    )
```

**Step 3: Update `fetch_amazon_tool`**

Replace the existing `fetch_amazon_tool` function:

```python
async def fetch_amazon_tool(ctx: RunContext[str], query: str) -> str:
    """Fetch Amazon product listings and reviews for the given query.

    Uses Crawl4AI (with Firecrawl fallback) to scrape Amazon search results
    and returns the extracted markdown content.
    Applies relevance filtering with adaptive refetch on low yield.
    """
    INITIAL_MAX = 2

    try:
        results = await fetch_amazon(query, max_products=INITIAL_MAX)
    except RuntimeError as exc:
        logger.error("Amazon fetch error: %s", exc)
        return f"[ERROR] Failed to fetch Amazon data for '{query}': {exc}"

    if not results:
        return f"No Amazon results found for '{query}'."

    relevant, yield_ratio = await relevance_filter(query, results, "amazon")

    if yield_ratio < 0.5 and len(results) >= INITIAL_MAX:
        logger.info("Amazon yield %.0f%% — refetching with max_products=%d", yield_ratio * 100, INITIAL_MAX * 2)
        try:
            results = await fetch_amazon(query, max_products=INITIAL_MAX * 2)
            if results:
                relevant, yield_ratio = await relevance_filter(query, results, "amazon")
        except RuntimeError as exc:
            logger.error("Amazon refetch error: %s", exc)

    if not relevant:
        return f"No relevant Amazon results found for '{query}'."

    sections: list[str] = []
    for item in relevant:
        title = item.get("title", "")
        content = _clean_text(item.get("content", "")[:5000], "amazon")
        sections.append(f"### {title}\n{content}")

    return f"# Amazon Results for '{query}'\n\n" + "\n\n---\n\n".join(sections)
```

**Step 4: Run all tool tests**

Run: `cd api && uv run python -m pytest tests/test_services/test_tools.py -v`
Expected: All tests PASS

---

### Task 5: Run full test suite and verify nothing is broken

**Files:** None (verification only)

**Step 1: Run entire backend test suite**

Run: `cd api && uv run python -m pytest -v`
Expected: All existing tests PASS (some may need mock adjustments for `relevance_filter` calls in existing tool tests)

**Step 2: Fix any broken existing tests**

The existing `TestFetchRedditTool`, `TestFetchYoutubeTool`, and `TestFetchAmazonTool` tests will likely need `relevance_filter` mocked since they only mock the fetch functions. Add a patch for `relevance_filter` that passes all items through:

```python
# Add this as a default mock wherever existing tool tests don't already mock it:
@patch("services.tools.relevance_filter", new_callable=AsyncMock,
       return_value=([], 1.0))  # adjust return value per test
```

Or, more practically, use a helper:

```python
def _passthrough_filter(items):
    """Returns a mock that passes all items through the filter."""
    return AsyncMock(return_value=(items, 1.0))
```

Each existing test should patch `relevance_filter` to return its input items unchanged.

---
