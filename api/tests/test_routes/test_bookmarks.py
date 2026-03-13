"""Tests for routes/bookmarks.py."""

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
    # Every chained call returns the same mock so the chain never breaks.
    chain.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.upsert.return_value = chain
    chain.delete.return_value = chain
    chain.execute.return_value = execute_result
    return chain


# ---------------------------------------------------------------------------
# list_bookmarks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_bookmarks_returns_data(authed_client):
    """GET /api/bookmarks/ returns bookmarks list."""
    mock_data = [
        {"id": "bm-1", "item_url": "https://example.com/a", "user_id": "test-user-id-123"}
    ]
    mock_client = _make_supabase_mock(mock_data)

    with patch("routes.bookmarks.get_supabase_client", return_value=mock_client):
        response = await authed_client.get("/api/bookmarks/")

    assert response.status_code == 200
    assert response.json() == {"bookmarks": mock_data}


@pytest.mark.asyncio
async def test_list_bookmarks_pagination(authed_client):
    """GET /api/bookmarks/?page=2&per_page=10 calls .range(10, 19)."""
    mock_client = _make_supabase_mock([])

    with patch("routes.bookmarks.get_supabase_client", return_value=mock_client):
        response = await authed_client.get("/api/bookmarks/?page=2&per_page=10")

    assert response.status_code == 200
    # offset = (2-1)*10 = 10, end = 10+10-1 = 19
    mock_client.range.assert_called_once_with(10, 19)


# ---------------------------------------------------------------------------
# create_bookmark
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_bookmark(authed_client):
    """POST /api/bookmarks/ returns created bookmark."""
    saved = {
        "id": "bm-new",
        "user_id": "test-user-id-123",
        "digest_id": "digest-abc",
        "item_url": "https://example.com/item",
        "item_title": "An Item",
    }
    mock_client = _make_supabase_mock([saved])

    with patch("routes.bookmarks.get_supabase_client", return_value=mock_client):
        response = await authed_client.post(
            "/api/bookmarks/",
            json={
                "digest_id": "digest-abc",
                "item_url": "https://example.com/item",
                "item_title": "An Item",
            },
        )

    assert response.status_code == 201
    assert response.json() == {"bookmark": saved}


@pytest.mark.asyncio
async def test_create_bookmark_empty_data(authed_client):
    """POST /api/bookmarks/ with empty resp.data returns {"bookmark": {}}."""
    mock_client = _make_supabase_mock([])

    with patch("routes.bookmarks.get_supabase_client", return_value=mock_client):
        response = await authed_client.post(
            "/api/bookmarks/",
            json={
                "digest_id": "digest-abc",
                "item_url": "https://example.com/item",
            },
        )

    assert response.status_code == 201
    assert response.json() == {"bookmark": {}}


# ---------------------------------------------------------------------------
# delete_bookmark
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_bookmark(authed_client):
    """DELETE /api/bookmarks/{id} returns 204 No Content."""
    mock_client = _make_supabase_mock([])

    with patch("routes.bookmarks.get_supabase_client", return_value=mock_client):
        response = await authed_client.delete("/api/bookmarks/bm-42")

    assert response.status_code == 204
    mock_client.delete.assert_called_once()
    mock_client.eq.assert_called_with("id", "bm-42")
