"""Tests for the GET /api/analyze/quota endpoint."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest


@pytest.mark.anyio
async def test_quota_requires_auth(client):
    """Unauthenticated requests should get 401/403."""
    resp = await client.get("/api/analyze/quota")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_quota_returns_correct_shape(authed_client):
    """Authenticated request returns daily_limit, remaining, resets_at."""
    with patch("routes.analyze.check_rate_limit", return_value=(True, 3)):
        resp = await authed_client.get("/api/analyze/quota")

    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_limit"] == 5
    assert data["remaining"] == 3
    assert "resets_at" in data
    # resets_at should be a valid ISO timestamp in the future
    resets_at = datetime.fromisoformat(data["resets_at"])
    assert resets_at > datetime.now(UTC)


@pytest.mark.anyio
async def test_quota_zero_remaining(authed_client):
    """When user has exhausted quota, remaining should be 0."""
    with patch("routes.analyze.check_rate_limit", return_value=(False, 0)):
        resp = await authed_client.get("/api/analyze/quota")

    assert resp.status_code == 200
    data = resp.json()
    assert data["remaining"] == 0
