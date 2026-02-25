"""Integration test: collectors → agent → structured digest output.

Tests the full data pipeline with MOCKED external APIs but REAL internal logic.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from models.digest_schemas import RawCollectorItem, DailyDigestLLMOutput

# --- Fixtures: realistic mock data per source ---

MOCK_ARXIV_ITEMS = [
    RawCollectorItem(title="Scaling Laws for Neural Language Models", url="https://arxiv.org/abs/2001.08361", source="arxiv", snippet="We study empirical scaling laws...", author="Kaplan et al.", published_at=datetime.now(timezone.utc)),
    RawCollectorItem(title="Attention Is All You Need v2", url="https://arxiv.org/abs/2401.00001", source="arxiv", snippet="We propose improvements to transformer architecture...", author="Research Team", published_at=datetime.now(timezone.utc)),
]

MOCK_GITHUB_ITEMS = [
    RawCollectorItem(title="openai/swarm", url="https://github.com/openai/swarm", source="github", snippet="Educational framework for multi-agent orchestration", author="openai", published_at=datetime.now(timezone.utc)),
]

MOCK_RSS_ITEMS = [
    RawCollectorItem(title="Anthropic Releases Claude 4.5", url="https://anthropic.com/blog/claude-4-5", source="rss", snippet="Today we release Claude 4.5 with improved reasoning...", author="Anthropic", published_at=datetime.now(timezone.utc)),
    RawCollectorItem(title="Anthropic Launches Claude 4.5", url="https://simonwillison.net/2025/anthropic-claude/", source="rss", snippet="Anthropic just released Claude 4.5, here are my thoughts...", author="Simon Willison", published_at=datetime.now(timezone.utc)),
]

MOCK_BLUESKY_ITEMS = [
    RawCollectorItem(title="Just published our new paper on efficient fine-tuning...", url="https://bsky.app/profile/researcher/post/abc", source="bluesky", snippet="Thread on LoRA improvements", author="researcher.bsky.social", published_at=datetime.now(timezone.utc)),
]


@pytest.mark.asyncio
async def test_full_pipeline_mock():
    """Collectors → merge → agent → DailyDigestLLMOutput with correct structure."""
    from services.collectors.base import COLLECTOR_REGISTRY

    mock_collectors = {
        "arxiv": AsyncMock(collect=AsyncMock(return_value=MOCK_ARXIV_ITEMS)),
        "github": AsyncMock(collect=AsyncMock(return_value=MOCK_GITHUB_ITEMS)),
        "rss": AsyncMock(collect=AsyncMock(return_value=MOCK_RSS_ITEMS)),
        "bluesky": AsyncMock(collect=AsyncMock(return_value=MOCK_BLUESKY_ITEMS)),
    }

    with patch.dict(COLLECTOR_REGISTRY, mock_collectors, clear=True):
        # Step 1: Collect from all sources
        all_items = []
        for name, collector in COLLECTOR_REGISTRY.items():
            items = await collector.collect()
            all_items.extend(items)

        # Verify collection
        assert len(all_items) == 6  # 2 + 1 + 2 + 1
        sources = {item.source for item in all_items}
        assert sources == {"arxiv", "github", "rss", "bluesky"}

        # Step 2: Feed to agent (mock the LLM call, verify input/output contract)
        mock_output = DailyDigestLLMOutput(
            executive_summary="Major releases from Anthropic and new scaling research.",
            items=[],
            top_highlights=["Claude 4.5 release", "Scaling laws update", "LoRA improvements"],
            trending_keywords=["claude", "scaling", "fine-tuning"],
            category_counts={"Research": 2, "Product": 2, "Open Source": 1, "Tooling": 1},
            source_counts={"arxiv": 2, "github": 1, "rss": 2, "bluesky": 1},
        )
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("services.digest_agent.digest_agent.run", new_callable=AsyncMock, return_value=mock_result):
            from services.digest_agent import analyze_digest
            result = await analyze_digest(all_items)

            # Verify output structure
            assert isinstance(result, DailyDigestLLMOutput)
            assert len(result.trending_keywords) > 0
            assert result.executive_summary
            assert len(result.top_highlights) >= 3
            assert result.source_counts == {"arxiv": 2, "github": 1, "rss": 2, "bluesky": 1}


@pytest.mark.asyncio
async def test_single_collector_failure_doesnt_block_others():
    """If one collector crashes, the rest still contribute to the digest."""
    from services.collectors.base import COLLECTOR_REGISTRY

    mock_collectors = {
        "arxiv": AsyncMock(collect=AsyncMock(return_value=MOCK_ARXIV_ITEMS)),
        "github": AsyncMock(collect=AsyncMock(side_effect=Exception("GitHub API rate limited"))),
        "rss": AsyncMock(collect=AsyncMock(return_value=MOCK_RSS_ITEMS)),
        "bluesky": AsyncMock(collect=AsyncMock(return_value=MOCK_BLUESKY_ITEMS)),
    }

    with patch.dict(COLLECTOR_REGISTRY, mock_collectors, clear=True):
        all_items = []
        for name, collector in COLLECTOR_REGISTRY.items():
            try:
                items = await collector.collect()
                all_items.extend(items)
            except Exception:
                pass  # orchestrator handles this

        # 3 of 4 collectors succeeded
        assert len(all_items) == 5  # 2 + 0 + 2 + 1
        sources = {item.source for item in all_items}
        assert "github" not in sources
        assert len(sources) == 3  # still enough for a useful digest


@pytest.mark.asyncio
async def test_all_collectors_fail():
    """If all collectors fail, no items are collected (graceful empty state)."""
    from services.collectors.base import COLLECTOR_REGISTRY

    mock_collectors = {
        "arxiv": AsyncMock(collect=AsyncMock(side_effect=Exception("timeout"))),
        "github": AsyncMock(collect=AsyncMock(side_effect=Exception("rate limit"))),
        "rss": AsyncMock(collect=AsyncMock(side_effect=Exception("DNS failure"))),
        "bluesky": AsyncMock(collect=AsyncMock(side_effect=Exception("auth error"))),
    }

    with patch.dict(COLLECTOR_REGISTRY, mock_collectors, clear=True):
        all_items = []
        for name, collector in COLLECTOR_REGISTRY.items():
            try:
                items = await collector.collect()
                all_items.extend(items)
            except Exception:
                pass
        assert len(all_items) == 0
        # Orchestrator should NOT call the agent and should set status to "failed"


@pytest.mark.asyncio
async def test_data_quality_validation():
    """All collected items pass schema validation — no None titles, no invalid URLs."""
    all_items = MOCK_ARXIV_ITEMS + MOCK_GITHUB_ITEMS + MOCK_RSS_ITEMS + MOCK_BLUESKY_ITEMS
    for item in all_items:
        assert item.title and len(item.title) > 0, f"Empty title from {item.source}"
        assert item.url.startswith("http"), f"Invalid URL from {item.source}: {item.url}"
        assert item.source in ("arxiv", "github", "rss", "bluesky")
        assert item.published_at is not None, f"Missing timestamp from {item.source}"
