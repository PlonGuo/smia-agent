"""Tests for AI Daily Report endpoints."""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from httpx import AsyncClient, ASGITransport
from core.auth import AuthenticatedUser


@pytest_asyncio.fixture
async def authed_client():
    """Create test client with mocked auth."""
    mock_user = AuthenticatedUser(user_id="test-user-1", access_token="test-token")

    from index import app
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


class TestGetTodayDigest:
    @pytest.mark.asyncio
    async def test_returns_completed_digest(self, authed_client):
        """Any authenticated user sees completed digest."""
        with patch("routes.ai_daily_report.claim_or_get_digest", return_value={
                 "status": "completed",
                 "digest_id": "d-1",
                 "digest": {"executive_summary": "Test"},
             }):
            resp = await authed_client.get("/api/ai-daily-report/today")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert data["digest"]["executive_summary"] == "Test"

    @pytest.mark.asyncio
    async def test_claimed_triggers_background(self, authed_client):
        """When claim is won, background task is started."""
        with patch("routes.ai_daily_report.claim_or_get_digest", return_value={
                 "status": "collecting",
                 "digest_id": "d-2",
                 "claimed": True,
             }), \
             patch("routes.ai_daily_report.run_digest", new_callable=AsyncMock):
            resp = await authed_client.get("/api/ai-daily-report/today")
            assert resp.status_code == 200
            assert resp.json()["claimed"] is True


class TestAccessStatus:
    @pytest.mark.asyncio
    async def test_returns_approved_for_any_user(self, authed_client):
        """All authenticated users get 'approved' status (open access)."""
        resp = await authed_client.get("/api/ai-daily-report/status")
        assert resp.status_code == 200
        assert resp.json()["access"] == "approved"


class TestRequestAccess:
    @pytest.mark.asyncio
    async def test_returns_already_authorized(self, authed_client):
        """With open access, all users are already authorized."""
        resp = await authed_client.post(
            "/api/ai-daily-report/access-request",
            json={"email": "user@test.com", "reason": "I need access"},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "already_authorized"
        assert resp.json()["access"] == "approved"


class TestListDigests:
    @pytest.mark.asyncio
    async def test_lists_completed(self, authed_client):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[{"id": "d-1", "digest_date": "2026-02-24", "status": "completed"}]
        )
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=1
        )

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.get("/api/ai-daily-report/list")
            assert resp.status_code == 200


class TestSharedDigest:
    @pytest.mark.asyncio
    async def test_invalid_token(self, authed_client):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = None

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.get("/api/ai-daily-report/shared/invalid-token")
            assert resp.status_code == 404
