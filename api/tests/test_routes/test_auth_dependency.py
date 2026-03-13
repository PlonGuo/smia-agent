"""Tests for core/auth.py — get_current_user dependency."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.auth import AuthenticatedUser, get_current_user  # noqa: E402


def _make_credentials(token: str) -> HTTPAuthorizationCredentials:
    """Build a fake HTTPAuthorizationCredentials with the given token."""
    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = token
    return creds


# ---------------------------------------------------------------------------
# valid token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_token_returns_user():
    """A valid token returns an AuthenticatedUser with the correct user_id."""
    mock_user = MagicMock()
    mock_user.id = "uid-123"

    mock_user_response = MagicMock()
    mock_user_response.user = mock_user

    mock_client = MagicMock()
    mock_client.auth.get_user.return_value = mock_user_response

    with patch("core.auth.get_supabase_client", return_value=mock_client):
        result = await get_current_user(credentials=_make_credentials("valid-jwt"))

    assert isinstance(result, AuthenticatedUser)
    assert result.user_id == "uid-123"
    assert result.access_token == "valid-jwt"


# ---------------------------------------------------------------------------
# user is None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_none_user_raises_401():
    """When client.auth.get_user returns a response with .user=None, raise 401."""
    mock_user_response = MagicMock()
    mock_user_response.user = None

    mock_client = MagicMock()
    mock_client.auth.get_user.return_value = mock_user_response

    with patch("core.auth.get_supabase_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=_make_credentials("expired-jwt"))

    assert exc_info.value.status_code == 401
    assert "Invalid or expired token" in exc_info.value.detail


# ---------------------------------------------------------------------------
# exception from supabase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exception_raises_401():
    """When client.auth.get_user raises an unexpected exception, raise 401."""
    mock_client = MagicMock()
    mock_client.auth.get_user.side_effect = Exception("boom")

    with patch("core.auth.get_supabase_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=_make_credentials("bad-jwt"))

    assert exc_info.value.status_code == 401
    assert "Invalid or expired token" in exc_info.value.detail


# ---------------------------------------------------------------------------
# missing credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_credentials_raises_401():
    """Calling get_current_user(None) raises 401 with 'Missing authorization header'."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None)

    assert exc_info.value.status_code == 401
    assert "Missing authorization header" in exc_info.value.detail
