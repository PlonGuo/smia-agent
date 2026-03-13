"""Tests for AI Daily Report endpoints."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from httpx import ASGITransport, AsyncClient

from core.auth import AuthenticatedUser


@pytest_asyncio.fixture
async def authed_client():
    """Create test client with mocked auth."""
    mock_user = AuthenticatedUser(user_id="test-user-1", access_token="test-token")

    from core.auth import get_current_user
    from index import app

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

    @pytest.mark.asyncio
    async def test_expired_token_returns_410(self, authed_client):
        """Lines 135-148: token_row has an expired expires_at — should return 410."""
        mock_client = MagicMock()

        # token_row.data with expired timestamp
        expired_time = "2020-01-01T00:00:00Z"
        mock_token_row = MagicMock()
        mock_token_row.data = {"digest_id": "d-99", "expires_at": expired_time}

        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_token_row

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.get("/api/ai-daily-report/shared/some-token")
            assert resp.status_code == 410
            assert "expired" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_valid_token_returns_digest(self, authed_client):
        """Lines 141-148: valid non-expired token returns digest data."""
        from datetime import UTC, datetime, timedelta

        mock_client = MagicMock()

        future_time = (datetime.now(UTC) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
        mock_token_row = MagicMock()
        mock_token_row.data = {"digest_id": "d-88", "expires_at": future_time}

        mock_digest_row = MagicMock()
        mock_digest_row.data = {"id": "d-88", "status": "completed", "executive_summary": "Good stuff"}

        # First table call returns token_row; second returns digest
        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_token_row
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_digest_row

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.get("/api/ai-daily-report/shared/valid-token")
            assert resp.status_code == 200
            assert resp.json()["digest"]["executive_summary"] == "Good stuff"

    @pytest.mark.asyncio
    async def test_token_row_no_expiry_returns_digest(self, authed_client):
        """Lines 135-148: token_row with no expires_at skips expiry check."""
        mock_client = MagicMock()

        mock_token_row = MagicMock()
        mock_token_row.data = {"digest_id": "d-77", "expires_at": None}

        mock_digest_row = MagicMock()
        mock_digest_row.data = {"id": "d-77", "status": "completed", "executive_summary": "No expiry"}

        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_token_row
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_digest_row

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.get("/api/ai-daily-report/shared/no-expiry-token")
            assert resp.status_code == 200
            assert resp.json()["digest"]["executive_summary"] == "No expiry"


class TestGetDigest:
    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, authed_client):
        """Lines 157-168: resp is None → 404."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = None

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.get("/api/ai-daily-report/nonexistent-id")
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_returns_digest_when_found(self, authed_client):
        """Lines 157-168: valid digest_id returns digest data."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = {"id": "d-found", "status": "completed", "executive_summary": "Hello"}

        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_resp

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.get("/api/ai-daily-report/d-found")
            assert resp.status_code == 200
            assert resp.json()["digest"]["executive_summary"] == "Hello"

    @pytest.mark.asyncio
    async def test_returns_404_when_data_is_empty(self, authed_client):
        """Lines 165-166: resp returned but .data is falsy → 404."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = None

        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_resp

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.get("/api/ai-daily-report/empty-id")
            assert resp.status_code == 404


class TestCreateShareToken:
    @pytest.mark.asyncio
    async def test_creates_token_and_returns_url(self, authed_client):
        """Lines 200-214: POST /share creates token and returns URL."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.post("/api/ai-daily-report/share?digest_id=d-123")
            assert resp.status_code == 200
            data = resp.json()
            assert "token" in data
            assert "url" in data
            assert "expires_at" in data
            assert "d-123" not in data["url"] or "/shared/" in data["url"]

    @pytest.mark.asyncio
    async def test_share_token_insert_called(self, authed_client):
        """Lines 204-209: verifies Supabase insert is called with right fields."""
        mock_client = MagicMock()
        insert_mock = MagicMock()
        mock_client.table.return_value.insert.return_value = insert_mock
        insert_mock.execute.return_value = MagicMock()

        with patch("routes.ai_daily_report.get_supabase_client", return_value=mock_client):
            resp = await authed_client.post("/api/ai-daily-report/share?digest_id=d-456")
            assert resp.status_code == 200

            # Verify the insert was called
            mock_client.table.assert_called_with("digest_share_tokens")
            call_args = mock_client.table.return_value.insert.call_args[0][0]
            assert call_args["digest_id"] == "d-456"
            assert "token" in call_args
            assert "expires_at" in call_args
