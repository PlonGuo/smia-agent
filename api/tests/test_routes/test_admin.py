"""Tests for admin routes."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# --- Mock is_admin for route-level auth ---


def _mock_is_admin_true(user_id, access_token):
    return True


def _mock_is_admin_false(user_id, access_token):
    return False


# --- Fixtures ---

MOCK_REQUEST = {
    "id": "req-1",
    "user_id": "user-abc",
    "email": "user@example.com",
    "reason": "I want access for research",
    "status": "pending",
    "rejection_reason": None,
    "reviewed_by": None,
    "reviewed_at": None,
    "created_at": "2026-02-24T00:00:00+00:00",
}

MOCK_ADMIN = {
    "id": "admin-1",
    "user_id": "test-user-id-123",
    "email": "admin@example.com",
    "created_at": "2026-02-24T00:00:00+00:00",
}


class TestListAccessRequests:
    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, authed_client):
        with patch("routes.admin.is_admin", _mock_is_admin_false):
            resp = await authed_client.get("/api/admin/requests")
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_list(self, authed_client):
        mock_execute = MagicMock()
        mock_execute.data = [MOCK_REQUEST]

        with patch("routes.admin.is_admin", _mock_is_admin_true), \
             patch("routes.admin.get_supabase_client") as mock_client:
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.execute.return_value = mock_execute
            mock_client.return_value.table.return_value = mock_table

            resp = await authed_client.get("/api/admin/requests")
            assert resp.status_code == 200
            data = resp.json()
            assert "requests" in data
            assert len(data["requests"]) == 1


class TestApproveRequest:
    @pytest.mark.asyncio
    async def test_approve_success(self, authed_client):
        mock_select_execute = MagicMock()
        mock_select_execute.data = MOCK_REQUEST

        mock_update_execute = MagicMock()
        mock_update_execute.data = [{**MOCK_REQUEST, "status": "approved"}]

        mock_upsert_execute = MagicMock()
        mock_upsert_execute.data = [{"id": "auth-1"}]

        with patch("routes.admin.is_admin", _mock_is_admin_true), \
             patch("routes.admin.get_supabase_client") as mock_client, \
             patch("routes.admin.send_approval_email") as mock_email:
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = mock_select_execute
            mock_table.update.return_value = mock_table
            mock_table.upsert.return_value = mock_table
            mock_client.return_value.table.return_value = mock_table

            resp = await authed_client.post("/api/admin/requests/req-1/approve")
            assert resp.status_code == 200
            assert resp.json()["status"] == "approved"
            mock_email.assert_called_once_with("user@example.com")

    @pytest.mark.asyncio
    async def test_approve_not_found(self, authed_client):
        with patch("routes.admin.is_admin", _mock_is_admin_true), \
             patch("routes.admin.get_supabase_client") as mock_client:
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = None  # maybe_single returns None
            mock_client.return_value.table.return_value = mock_table

            resp = await authed_client.post("/api/admin/requests/nonexistent/approve")
            assert resp.status_code == 404


class TestRejectRequest:
    @pytest.mark.asyncio
    async def test_reject_success(self, authed_client):
        mock_select_execute = MagicMock()
        mock_select_execute.data = MOCK_REQUEST

        with patch("routes.admin.is_admin", _mock_is_admin_true), \
             patch("routes.admin.get_supabase_client") as mock_client, \
             patch("routes.admin.send_rejection_email") as mock_email:
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = mock_select_execute
            mock_table.update.return_value = mock_table
            mock_client.return_value.table.return_value = mock_table

            resp = await authed_client.post(
                "/api/admin/requests/req-1/reject", params={"reason": "Not enough info"}
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "rejected"
            mock_email.assert_called_once_with("user@example.com", "Not enough info")


class TestListAdmins:
    @pytest.mark.asyncio
    async def test_list_admins(self, authed_client):
        mock_execute = MagicMock()
        mock_execute.data = [MOCK_ADMIN]

        with patch("routes.admin.is_admin", _mock_is_admin_true), \
             patch("routes.admin.get_supabase_client") as mock_client:
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.execute.return_value = mock_execute
            mock_client.return_value.table.return_value = mock_table

            resp = await authed_client.get("/api/admin/admins")
            assert resp.status_code == 200
            assert len(resp.json()["admins"]) == 1


class TestRemoveAdmin:
    @pytest.mark.asyncio
    async def test_cannot_remove_self(self, authed_client):
        mock_execute = MagicMock()
        mock_execute.data = {"user_id": "test-user-id-123"}

        with patch("routes.admin.is_admin", _mock_is_admin_true), \
             patch("routes.admin.get_supabase_client") as mock_client:
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute.return_value = mock_execute
            mock_client.return_value.table.return_value = mock_table

            resp = await authed_client.delete("/api/admin/admins/admin-1")
            assert resp.status_code == 400
            assert "Cannot remove yourself" in resp.json()["detail"]
