"""Tests for arXiv collector."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def _make_mock_result(title="Test Paper", authors=None, summary="A test paper."):
    """Create a mock arxiv.Result object."""
    result = MagicMock()
    result.title = title
    result.entry_id = "http://arxiv.org/abs/2401.00001v1"
    result.summary = summary
    result.published = datetime(2026, 2, 24, tzinfo=timezone.utc)
    if authors is None:
        author = MagicMock()
        author.__str__ = lambda self: "John Doe"
        result.authors = [author]
    else:
        result.authors = authors
    return result


class TestArxivCollector:
    @pytest.mark.asyncio
    async def test_returns_items(self):
        mock_results = [_make_mock_result(), _make_mock_result(title="Paper 2")]

        with patch("services.collectors.arxiv_collector.arxiv") as mock_arxiv:
            mock_client = MagicMock()
            mock_client.results.return_value = mock_results
            mock_arxiv.Client.return_value = mock_client
            mock_arxiv.Search = MagicMock()
            mock_arxiv.SortCriterion.SubmittedDate = "submittedDate"

            from services.collectors.arxiv_collector import ArxivCollector
            items = await ArxivCollector().collect()

            assert len(items) == 2
            assert items[0].source == "arxiv"
            assert items[0].title == "Test Paper"
            assert "arxiv.org" in items[0].url
            assert items[0].published_at is not None

    @pytest.mark.asyncio
    async def test_empty_results(self):
        with patch("services.collectors.arxiv_collector.arxiv") as mock_arxiv:
            mock_client = MagicMock()
            mock_client.results.return_value = []
            mock_arxiv.Client.return_value = mock_client
            mock_arxiv.Search = MagicMock()
            mock_arxiv.SortCriterion.SubmittedDate = "submittedDate"

            from services.collectors.arxiv_collector import ArxivCollector
            items = await ArxivCollector().collect()
            assert items == []

    @pytest.mark.asyncio
    async def test_missing_authors(self):
        result = _make_mock_result(authors=[])

        with patch("services.collectors.arxiv_collector.arxiv") as mock_arxiv:
            mock_client = MagicMock()
            mock_client.results.return_value = [result]
            mock_arxiv.Client.return_value = mock_client
            mock_arxiv.Search = MagicMock()
            mock_arxiv.SortCriterion.SubmittedDate = "submittedDate"

            from services.collectors.arxiv_collector import ArxivCollector
            items = await ArxivCollector().collect()
            assert len(items) == 1
            assert items[0].author is None

    @pytest.mark.asyncio
    async def test_snippet_truncated(self):
        long_summary = "A" * 500
        result = _make_mock_result(summary=long_summary)

        with patch("services.collectors.arxiv_collector.arxiv") as mock_arxiv:
            mock_client = MagicMock()
            mock_client.results.return_value = [result]
            mock_arxiv.Client.return_value = mock_client
            mock_arxiv.Search = MagicMock()
            mock_arxiv.SortCriterion.SubmittedDate = "submittedDate"

            from services.collectors.arxiv_collector import ArxivCollector
            items = await ArxivCollector().collect()
            assert len(items[0].snippet) <= 300

    @pytest.mark.asyncio
    async def test_api_error_returns_empty(self):
        with patch("services.collectors.arxiv_collector.arxiv") as mock_arxiv:
            mock_client = MagicMock()
            mock_client.results.side_effect = Exception("Network timeout")
            mock_arxiv.Client.return_value = mock_client
            mock_arxiv.Search = MagicMock()
            mock_arxiv.SortCriterion.SubmittedDate = "submittedDate"

            from services.collectors.arxiv_collector import ArxivCollector
            items = await ArxivCollector().collect()
            assert items == []
