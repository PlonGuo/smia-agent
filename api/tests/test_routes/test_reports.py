"""Tests for Reports CRUD endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.conftest import make_trend_report_data


class TestListReports:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        resp = await client.get("/api/reports")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_returns_paginated_reports(self, authed_client):
        reports = [make_trend_report_data(topic=f"Topic {i}") for i in range(3)]
        with patch("routes.reports.get_reports", return_value=(reports, 3)):
            resp = await authed_client.get("/api/reports?page=1&per_page=10")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert len(body["reports"]) == 3

    @pytest.mark.asyncio
    async def test_filters_by_sentiment(self, authed_client):
        with patch("routes.reports.get_reports", return_value=([], 0)) as mock:
            await authed_client.get("/api/reports?sentiment=Positive")
            mock.assert_called_once()
            call_kwargs = mock.call_args[1]
            assert call_kwargs["sentiment"] == "Positive"

    @pytest.mark.asyncio
    async def test_search_parameter(self, authed_client):
        with patch("routes.reports.get_reports", return_value=([], 0)) as mock:
            await authed_client.get("/api/reports?search=plaud")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["search"] == "plaud"


class TestGetReport:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        resp = await client.get("/api/reports/some-id")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_returns_report(self, authed_client):
        report = make_trend_report_data(id="report-123")
        with patch("routes.reports.get_report_by_id", return_value=report):
            resp = await authed_client.get("/api/reports/report-123")

        assert resp.status_code == 200
        assert resp.json()["topic"] == "Test Topic"

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, authed_client):
        with patch("routes.reports.get_report_by_id", return_value=None):
            resp = await authed_client.get("/api/reports/nonexistent")

        assert resp.status_code == 404


class TestDeleteReport:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        resp = await client.delete("/api/reports/some-id")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_deletes_report(self, authed_client):
        with patch("routes.reports.delete_report", return_value=True):
            resp = await authed_client.delete("/api/reports/report-123")

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, authed_client):
        with patch("routes.reports.delete_report", return_value=False):
            resp = await authed_client.delete("/api/reports/nonexistent")

        assert resp.status_code == 404
