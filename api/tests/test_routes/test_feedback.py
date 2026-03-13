"""Tests for routes/feedback.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def _make_supabase_mock(data):
    """Return a mock whose full Supabase chain resolves to data."""
    execute_result = MagicMock()
    execute_result.data = data

    chain = MagicMock()
    chain.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.upsert.return_value = chain
    chain.execute.return_value = execute_result
    return chain


# ---------------------------------------------------------------------------
# vote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vote_upvote(authed_client):
    """POST /api/feedback/vote with vote=1 returns saved feedback."""
    saved = {
        "id": "fb-1",
        "user_id": "test-user-id-123",
        "digest_id": "digest-xyz",
        "item_url": "https://example.com/item",
        "vote": 1,
    }
    mock_client = _make_supabase_mock([saved])

    with patch("routes.feedback.get_supabase_client", return_value=mock_client):
        response = await authed_client.post(
            "/api/feedback/vote",
            json={"digest_id": "digest-xyz", "item_url": "https://example.com/item", "vote": 1},
        )

    assert response.status_code == 201
    assert response.json() == {"feedback": saved}


@pytest.mark.asyncio
async def test_vote_downvote(authed_client):
    """POST /api/feedback/vote with vote=-1 returns saved feedback."""
    saved = {
        "id": "fb-2",
        "user_id": "test-user-id-123",
        "digest_id": "digest-xyz",
        "item_url": None,
        "vote": -1,
    }
    mock_client = _make_supabase_mock([saved])

    with patch("routes.feedback.get_supabase_client", return_value=mock_client):
        response = await authed_client.post(
            "/api/feedback/vote",
            json={"digest_id": "digest-xyz", "vote": -1},
        )

    assert response.status_code == 201
    assert response.json() == {"feedback": saved}


@pytest.mark.asyncio
async def test_vote_empty_data(authed_client):
    """POST /api/feedback/vote when resp.data is empty returns {"feedback": {}}."""
    mock_client = _make_supabase_mock([])

    with patch("routes.feedback.get_supabase_client", return_value=mock_client):
        response = await authed_client.post(
            "/api/feedback/vote",
            json={"digest_id": "digest-xyz", "vote": 1},
        )

    assert response.status_code == 201
    assert response.json() == {"feedback": {}}


# ---------------------------------------------------------------------------
# get_digest_feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_digest_feedback(authed_client):
    """GET /api/feedback/digest/{id} returns list of votes."""
    votes = [
        {"id": "fb-1", "digest_id": "digest-abc", "vote": 1},
        {"id": "fb-2", "digest_id": "digest-abc", "vote": -1},
    ]
    mock_client = _make_supabase_mock(votes)

    with patch("routes.feedback.get_supabase_client", return_value=mock_client):
        response = await authed_client.get("/api/feedback/digest/digest-abc")

    assert response.status_code == 200
    assert response.json() == {"votes": votes}


@pytest.mark.asyncio
async def test_get_digest_feedback_empty(authed_client):
    """GET /api/feedback/digest/{id} returns {"votes": []} when no feedback."""
    mock_client = _make_supabase_mock([])

    with patch("routes.feedback.get_supabase_client", return_value=mock_client):
        response = await authed_client.get("/api/feedback/digest/digest-no-votes")

    assert response.status_code == 200
    assert response.json() == {"votes": []}
