"""Tests for digest agent."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from models.digest_schemas import (
    RawCollectorItem,
    DailyDigestLLMOutput,
    DigestItem,
)


def _make_sample_items():
    """Create sample collector items for testing."""
    return [
        RawCollectorItem(
            title="Scaling Laws for Neural Language Models",
            url="https://arxiv.org/abs/2401.00001",
            source="arxiv",
            snippet="We study empirical scaling laws for neural language models.",
            author="Kaplan et al.",
            published_at=datetime.now(timezone.utc),
        ),
        RawCollectorItem(
            title="openai/swarm",
            url="https://github.com/openai/swarm",
            source="github",
            snippet="Educational framework for multi-agent orchestration",
            author="openai",
            published_at=datetime.now(timezone.utc),
        ),
        RawCollectorItem(
            title="Anthropic Releases Claude 4.5",
            url="https://anthropic.com/blog/claude-4-5",
            source="rss",
            snippet="Today we release Claude 4.5 with improved reasoning.",
            author="Anthropic",
            published_at=datetime.now(timezone.utc),
        ),
    ]


def _make_mock_llm_output():
    """Create a mock DailyDigestLLMOutput."""
    return DailyDigestLLMOutput(
        executive_summary="Major releases from Anthropic and new scaling research dominate today.",
        items=[
            DigestItem(
                title="Anthropic Releases Claude 4.5",
                url="https://anthropic.com/blog/claude-4-5",
                source="rss",
                category="Product",
                importance=5,
                why_it_matters="New Claude model with significantly improved reasoning capabilities",
                also_on=["bluesky"],
            ),
            DigestItem(
                title="Scaling Laws for Neural Language Models",
                url="https://arxiv.org/abs/2401.00001",
                source="arxiv",
                category="Research",
                importance=4,
                why_it_matters="Establishes predictable scaling relationships for LLM training",
            ),
        ],
        top_highlights=[
            "Claude 4.5 released with improved reasoning",
            "New scaling laws paper from Kaplan et al.",
            "OpenAI multi-agent framework goes open source",
        ],
        trending_keywords=["claude", "scaling", "multi-agent", "reasoning"],
        category_counts={"Product": 1, "Research": 1},
        source_counts={"rss": 1, "arxiv": 1},
    )


class TestAnalyzeDigest:
    @pytest.mark.asyncio
    async def test_returns_structured_output(self):
        mock_output = _make_mock_llm_output()
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("services.digest_agent.digest_agent.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            from services.digest_agent import analyze_digest
            result = await analyze_digest(_make_sample_items())

            assert isinstance(result, DailyDigestLLMOutput)
            assert len(result.items) == 2
            assert len(result.top_highlights) == 3
            assert result.executive_summary
            assert "claude" in [kw.lower() for kw in result.trending_keywords]

    @pytest.mark.asyncio
    async def test_passes_all_items_to_agent(self):
        mock_result = MagicMock()
        mock_result.output = _make_mock_llm_output()

        with patch("services.digest_agent.digest_agent.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            from services.digest_agent import analyze_digest
            items = _make_sample_items()
            await analyze_digest(items)

            # Verify the agent was called with all items in the prompt
            call_args = mock_run.call_args[0][0]
            assert "arxiv" in call_args
            assert "github" in call_args
            assert "rss" in call_args
            assert "3 items" in call_args

    @pytest.mark.asyncio
    async def test_handles_empty_items(self):
        mock_result = MagicMock()
        mock_result.output = DailyDigestLLMOutput(
            executive_summary="No significant items today.",
            items=[],
            top_highlights=["No highlights", "Nothing notable", "Quiet day"],
            trending_keywords=[],
            category_counts={},
            source_counts={},
        )

        with patch("services.digest_agent.digest_agent.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            from services.digest_agent import analyze_digest
            result = await analyze_digest([])

            assert result.items == []
            assert result.executive_summary == "No significant items today."
