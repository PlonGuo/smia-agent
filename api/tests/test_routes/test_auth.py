"""Tests for auth & binding endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestGenerateBindCode:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        resp = await client.get("/api/bind/code")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_generates_code(self, authed_client):
        mock_row = {
            "user_id": "test-user-id-123",
            "bind_code": "ABC123",
            "code_expires_at": "2026-02-14T00:10:00+00:00",
        }
        with patch("routes.auth.save_bind_code", return_value=mock_row):
            resp = await authed_client.get("/api/bind/code")

        assert resp.status_code == 200
        body = resp.json()
        assert "bind_code" in body
        assert len(body["bind_code"]) == 6
        assert "expires_at" in body


class TestConfirmBinding:
    @pytest.mark.asyncio
    async def test_valid_binding(self, client):
        """bind/confirm does NOT require auth (called by bot)."""
        mock_binding = {
            "user_id": "test-user-id-123",
            "bind_code": "ABC123",
            "code_expires_at": "2099-01-01T00:00:00+00:00",
        }
        mock_result = {"user_id": "test-user-id-123", "telegram_user_id": 12345}

        with patch("routes.auth.lookup_bind_code", return_value=mock_binding):
            with patch("routes.auth.complete_binding", return_value=mock_result):
                resp = await client.post(
                    "/api/bind/confirm",
                    json={"telegram_user_id": 12345, "bind_code": "ABC123"},
                )

        assert resp.status_code == 200
        assert resp.json()["status"] == "bound"

    @pytest.mark.asyncio
    async def test_invalid_code_returns_404(self, client):
        with patch("routes.auth.lookup_bind_code", return_value=None):
            resp = await client.post(
                "/api/bind/confirm",
                json={"telegram_user_id": 12345, "bind_code": "BADCDE"},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_validates_code_length(self, client):
        resp = await client.post(
            "/api/bind/confirm",
            json={"telegram_user_id": 12345, "bind_code": "AB"},
        )
        assert resp.status_code == 422
