"""Tests for POST /api/analyze."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import make_trend_report_data


class TestAnalyzeEndpoint:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        """Unauthenticated requests should get 401/403."""
        resp = await client.post("/api/analyze", json={"query": "test topic"})
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_validates_query_too_short(self, authed_client):
        resp = await authed_client.post("/api/analyze", json={"query": "ab"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_validates_query_missing(self, authed_client):
        resp = await authed_client.post("/api/analyze", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_successful_analysis(self, authed_client):
        from models.schemas import TrendReport

        report_data = make_trend_report_data()
        mock_report = TrendReport(**report_data)

        with patch("routes.analyze.analyze_topic", new_callable=AsyncMock) as mock:
            mock.return_value = (mock_report, False)  # (report, cached)
            resp = await authed_client.post(
                "/api/analyze", json={"query": "test topic"}
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Analysis complete"
        assert body["report"]["topic"] == "Test Topic"
        assert body["cached"] is False

    @pytest.mark.asyncio
    async def test_cached_analysis(self, authed_client):
        from models.schemas import TrendReport

        report_data = make_trend_report_data()
        mock_report = TrendReport(**report_data)

        with patch("routes.analyze.analyze_topic", new_callable=AsyncMock) as mock:
            mock.return_value = (mock_report, True)  # cached hit
            resp = await authed_client.post(
                "/api/analyze", json={"query": "test topic", "time_range": "month"}
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["cached"] is True

    @pytest.mark.asyncio
    async def test_accepts_time_range(self, authed_client):
        from models.schemas import TrendReport

        report_data = make_trend_report_data()
        mock_report = TrendReport(**report_data)

        with patch("routes.analyze.analyze_topic", new_callable=AsyncMock) as mock:
            mock.return_value = (mock_report, False)
            resp = await authed_client.post(
                "/api/analyze", json={"query": "test topic", "time_range": "year"}
            )

        assert resp.status_code == 200
        # Verify time_range was passed to analyze_topic
        mock.assert_called_once()
        call_kwargs = mock.call_args
        assert call_kwargs.kwargs.get("time_range") == "year" or \
               (len(call_kwargs.args) > 0 and "year" in str(call_kwargs))

    @pytest.mark.asyncio
    async def test_handles_agent_error(self, authed_client):
        with patch(
            "routes.analyze.analyze_topic",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM timeout"),
        ):
            resp = await authed_client.post(
                "/api/analyze", json={"query": "test topic"}
            )

        assert resp.status_code == 500
        assert "Analysis failed" in resp.json()["detail"]
