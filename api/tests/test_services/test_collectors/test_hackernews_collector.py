"""Tests for Hacker News collector."""

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def _make_hit(
    title="Test Story",
    url="https://example.com/story",
    object_id="12345",
    author="hnuser",
    created_at="2026-03-12T10:00:00.000Z",
    story_text=None,
    points=100,
):
    return {
        "title": title,
        "url": url,
        "objectID": object_id,
        "author": author,
        "created_at": created_at,
        "story_text": story_text,
        "points": points,
        "num_comments": 42,
    }


def _make_mock_client(json_data: dict):
    """Build a mock httpx.AsyncClient context manager that returns json_data."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = json_data

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    return mock_client_instance


class TestHackernewsCollector:
    @pytest.mark.asyncio
    async def test_returns_items(self):
        hits = [_make_hit(title="Story 1"), _make_hit(title="Story 2", object_id="99999")]
        json_data = {"hits": hits}

        with patch("services.collectors.hackernews_collector.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.hackernews_collector import HackernewsCollector

            items = await HackernewsCollector().collect()

        assert len(items) == 2
        assert items[0].source == "hackernews"
        assert items[0].title == "Story 1"
        assert items[1].title == "Story 2"

    @pytest.mark.asyncio
    async def test_skips_empty_title(self):
        hits = [
            _make_hit(title=""),  # should be skipped
            _make_hit(title="Valid Story"),
        ]
        json_data = {"hits": hits}

        with patch("services.collectors.hackernews_collector.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.hackernews_collector import HackernewsCollector

            items = await HackernewsCollector().collect()

        assert len(items) == 1
        assert items[0].title == "Valid Story"

    @pytest.mark.asyncio
    async def test_uses_hn_url_fallback(self):
        hit = _make_hit(title="Discussion Only", url=None, object_id="55555")
        del hit["url"]  # ensure key is absent, not just None
        json_data = {"hits": [hit]}

        with patch("services.collectors.hackernews_collector.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.hackernews_collector import HackernewsCollector

            items = await HackernewsCollector().collect()

        assert len(items) == 1
        assert items[0].url == "https://news.ycombinator.com/item?id=55555"

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        with patch("services.collectors.hackernews_collector.httpx.AsyncClient") as mock_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.hackernews_collector import HackernewsCollector

            items = await HackernewsCollector().collect()

        assert items == []

    @pytest.mark.asyncio
    async def test_parses_published_at(self):
        hit = _make_hit(title="Dated Story", created_at="2026-03-12T10:30:00.000Z")
        json_data = {"hits": [hit]}

        with patch("services.collectors.hackernews_collector.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.hackernews_collector import HackernewsCollector

            items = await HackernewsCollector().collect()

        assert len(items) == 1
        assert isinstance(items[0].published_at, datetime)
        assert items[0].published_at == datetime(2026, 3, 12, 10, 30, 0, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_invalid_date_still_returns_item(self):
        hit = _make_hit(title="Bad Date Story", created_at="not-a-date")
        json_data = {"hits": [hit]}

        with patch("services.collectors.hackernews_collector.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.hackernews_collector import HackernewsCollector

            items = await HackernewsCollector().collect()

        assert len(items) == 1
        assert items[0].published_at is None

    @pytest.mark.asyncio
    async def test_empty_hits_returns_empty(self):
        json_data = {"hits": []}

        with patch("services.collectors.hackernews_collector.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.hackernews_collector import HackernewsCollector

            items = await HackernewsCollector().collect()

        assert items == []
