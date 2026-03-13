"""Tests for Guardian collector."""

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def _make_article(
    title="Test Article",
    url="https://guardian.com/world/test",
    pub_date="2026-03-12T10:00:00Z",
    trail_text="Some trail text",
    byline="John Doe",
    guardian_id="world/test-article",
):
    return {
        "webTitle": title,
        "webUrl": url,
        "webPublicationDate": pub_date,
        "fields": {"trailText": trail_text, "byline": byline},
        "id": guardian_id,
    }


def _mock_response(articles):
    resp = MagicMock()
    resp.json.return_value = {"response": {"results": articles}}
    resp.raise_for_status = MagicMock()
    return resp


class TestGuardianCollector:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty(self):
        from services.collectors.guardian_collector import GuardianCollector

        with patch("services.collectors.guardian_collector.settings") as mock_settings:
            mock_settings.guardian_api_key = ""
            collector = GuardianCollector()
            result = await collector.collect()

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_items(self):
        from services.collectors.guardian_collector import GuardianCollector

        articles = [_make_article(title="Article 1"), _make_article(title="Article 2", guardian_id="world/article-2")]

        with patch("services.collectors.guardian_collector.settings") as mock_settings:
            mock_settings.guardian_api_key = "test-key"
            with patch("services.collectors.guardian_collector.httpx.AsyncClient") as mock_cls:
                mock_instance = AsyncMock()
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_instance.get = AsyncMock(return_value=_mock_response(articles))

                collector = GuardianCollector()
                result = await collector.collect()

        assert len(result) == 2
        assert result[0].source == "guardian"
        assert result[1].source == "guardian"

    @pytest.mark.asyncio
    async def test_multiple_sections(self):
        from services.collectors.guardian_collector import GuardianCollector

        with patch("services.collectors.guardian_collector.settings") as mock_settings:
            mock_settings.guardian_api_key = "test-key"
            with patch("services.collectors.guardian_collector.httpx.AsyncClient") as mock_cls:
                mock_instance = AsyncMock()
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                # Each section call returns 1 article
                mock_instance.get = AsyncMock(return_value=_mock_response([_make_article()]))

                collector = GuardianCollector(sections=["world", "tech"])
                result = await collector.collect()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_section_failure_continues(self):
        from services.collectors.guardian_collector import GuardianCollector

        success_response = _mock_response([_make_article(title="Success Article")])

        with patch("services.collectors.guardian_collector.settings") as mock_settings:
            mock_settings.guardian_api_key = "test-key"
            with patch("services.collectors.guardian_collector.httpx.AsyncClient") as mock_cls:
                mock_instance = AsyncMock()
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                # First call raises, second succeeds
                mock_instance.get = AsyncMock(
                    side_effect=[Exception("Network error"), success_response]
                )

                collector = GuardianCollector(sections=["world", "tech"])
                result = await collector.collect()

        assert len(result) == 1
        assert result[0].title == "Success Article"

    @pytest.mark.asyncio
    async def test_keywords_added_to_params(self):
        from services.collectors.guardian_collector import GuardianCollector

        with patch("services.collectors.guardian_collector.settings") as mock_settings:
            mock_settings.guardian_api_key = "test-key"
            with patch("services.collectors.guardian_collector.httpx.AsyncClient") as mock_cls:
                mock_instance = AsyncMock()
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_instance.get = AsyncMock(return_value=_mock_response([]))

                collector = GuardianCollector(keywords=["AI", "ML"])
                await collector.collect()

        call_kwargs = mock_instance.get.call_args
        params = call_kwargs[1].get("params") or call_kwargs[0][1]
        assert params["q"] == "AI OR ML"

    @pytest.mark.asyncio
    async def test_no_keywords_no_q_param(self):
        from services.collectors.guardian_collector import GuardianCollector

        with patch("services.collectors.guardian_collector.settings") as mock_settings:
            mock_settings.guardian_api_key = "test-key"
            with patch("services.collectors.guardian_collector.httpx.AsyncClient") as mock_cls:
                mock_instance = AsyncMock()
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_instance.get = AsyncMock(return_value=_mock_response([]))

                collector = GuardianCollector()
                await collector.collect()

        call_kwargs = mock_instance.get.call_args
        params = call_kwargs[1].get("params") or call_kwargs[0][1]
        assert "q" not in params

    @pytest.mark.asyncio
    async def test_parses_published_at(self):
        from services.collectors.guardian_collector import GuardianCollector

        article = _make_article(pub_date="2026-03-12T10:00:00Z")

        with patch("services.collectors.guardian_collector.settings") as mock_settings:
            mock_settings.guardian_api_key = "test-key"
            with patch("services.collectors.guardian_collector.httpx.AsyncClient") as mock_cls:
                mock_instance = AsyncMock()
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_instance.get = AsyncMock(return_value=_mock_response([article]))

                collector = GuardianCollector()
                result = await collector.collect()

        assert len(result) == 1
        assert isinstance(result[0].published_at, datetime)
        assert result[0].published_at == datetime(2026, 3, 12, 10, 0, 0, tzinfo=UTC)

    def test_defaults_to_world_section(self):
        from services.collectors.guardian_collector import GuardianCollector

        collector = GuardianCollector()
        assert collector._sections == ["world"]
