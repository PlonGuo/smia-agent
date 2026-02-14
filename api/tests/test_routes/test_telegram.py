"""Tests for the Telegram webhook endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def _make_update(text: str, user_id: int = 12345, chat_id: int = 12345) -> dict:
    """Create a minimal Telegram Update payload."""
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "from": {"id": user_id, "first_name": "Test"},
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
        },
    }


class TestTelegramWebhook:
    @pytest.mark.asyncio
    async def test_returns_ok(self, client):
        """Webhook returns 200 OK for any valid JSON."""
        with patch("routes.telegram.handle_update", new_callable=AsyncMock):
            resp = await client.post(
                "/telegram/webhook",
                json=_make_update("/start"),
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_returns_400_for_invalid_json(self, client):
        """Webhook returns 400 for non-JSON bodies."""
        resp = await client.post(
            "/telegram/webhook",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_dispatches_to_handler(self, client):
        """Webhook dispatches the update to handle_update."""
        mock_handler = AsyncMock()
        with patch("routes.telegram.handle_update", mock_handler):
            await client.post(
                "/telegram/webhook",
                json=_make_update("/help"),
            )
        # BackgroundTasks execution is automatic in test client
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_update_still_ok(self, client):
        """An empty update dict still returns 200."""
        with patch("routes.telegram.handle_update", new_callable=AsyncMock):
            resp = await client.post("/telegram/webhook", json={})
        assert resp.status_code == 200
