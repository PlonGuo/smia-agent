"""Tests for Currents API news collector."""

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def _make_article(
    title="Test Article",
    url="https://example.com/article",
    description="A short description.",
    author="Jane Doe",
    published="2026-03-12T10:00:00.000Z",
    category=None,
    image=None,
):
    return {
        "title": title,
        "url": url,
        "description": description,
        "author": author,
        "published": published,
        "category": category or ["technology"],
        "image": image,
    }


def _make_mock_client(json_data: dict):
    """Build a mock httpx.AsyncClient context manager that returns json_data."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = json_data

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    return mock_client_instance


class TestCurrentsCollector:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty(self):
        with patch("services.collectors.currents_collector.settings") as mock_settings:
            mock_settings.currents_api_key = ""

            from services.collectors.currents_collector import CurrentsCollector

            items = await CurrentsCollector().collect()

        assert items == []

    @pytest.mark.asyncio
    async def test_returns_items(self):
        articles = [_make_article(title="Article 1"), _make_article(title="Article 2")]
        json_data = {"news": articles}

        with patch("services.collectors.currents_collector.settings") as mock_settings, \
             patch("services.collectors.currents_collector.httpx.AsyncClient") as mock_cls:
            mock_settings.currents_api_key = "test-api-key"
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.currents_collector import CurrentsCollector

            items = await CurrentsCollector().collect()

        assert len(items) == 2
        assert items[0].source == "currents"
        assert items[0].title == "Article 1"
        assert items[1].title == "Article 2"

    @pytest.mark.asyncio
    async def test_skips_empty_title(self):
        articles = [
            _make_article(title=""),  # should be skipped
            _make_article(title="Real Article"),
        ]
        json_data = {"news": articles}

        with patch("services.collectors.currents_collector.settings") as mock_settings, \
             patch("services.collectors.currents_collector.httpx.AsyncClient") as mock_cls:
            mock_settings.currents_api_key = "test-api-key"
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.currents_collector import CurrentsCollector

            items = await CurrentsCollector().collect()

        assert len(items) == 1
        assert items[0].title == "Real Article"

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        with patch("services.collectors.currents_collector.settings") as mock_settings, \
             patch("services.collectors.currents_collector.httpx.AsyncClient") as mock_cls:
            mock_settings.currents_api_key = "test-api-key"
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=Exception("Timeout"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.currents_collector import CurrentsCollector

            items = await CurrentsCollector().collect()

        assert items == []

    @pytest.mark.asyncio
    async def test_parses_published_at(self):
        article = _make_article(title="Dated Article", published="2026-03-12T14:30:00.000+00:00")
        json_data = {"news": [article]}

        with patch("services.collectors.currents_collector.settings") as mock_settings, \
             patch("services.collectors.currents_collector.httpx.AsyncClient") as mock_cls:
            mock_settings.currents_api_key = "test-api-key"
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.currents_collector import CurrentsCollector

            items = await CurrentsCollector().collect()

        assert len(items) == 1
        assert isinstance(items[0].published_at, datetime)
        assert items[0].published_at == datetime(2026, 3, 12, 14, 30, 0, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_z_suffix_handled(self):
        article = _make_article(title="Z Suffix Article", published="2026-03-12T10:00:00Z")
        json_data = {"news": [article]}

        with patch("services.collectors.currents_collector.settings") as mock_settings, \
             patch("services.collectors.currents_collector.httpx.AsyncClient") as mock_cls:
            mock_settings.currents_api_key = "test-api-key"
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.currents_collector import CurrentsCollector

            items = await CurrentsCollector().collect()

        assert len(items) == 1
        assert isinstance(items[0].published_at, datetime)
        assert items[0].published_at == datetime(2026, 3, 12, 10, 0, 0, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_description_truncated(self):
        long_description = "X" * 500
        article = _make_article(title="Long Desc Article", description=long_description)
        json_data = {"news": [article]}

        with patch("services.collectors.currents_collector.settings") as mock_settings, \
             patch("services.collectors.currents_collector.httpx.AsyncClient") as mock_cls:
            mock_settings.currents_api_key = "test-api-key"
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=_make_mock_client(json_data))
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.collectors.currents_collector import CurrentsCollector

            items = await CurrentsCollector().collect()

        assert len(items) == 1
        assert len(items[0].snippet) == 300
        assert items[0].snippet == "X" * 300
