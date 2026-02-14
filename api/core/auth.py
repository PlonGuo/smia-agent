"""Supabase JWT auth dependency for FastAPI."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from services.database import get_supabase_client

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    """Holds the verified user ID and access token extracted from the JWT."""

    user_id: str
    access_token: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency that validates the Supabase JWT.

    Extracts the Bearer token from the Authorization header, calls
    ``supabase.auth.get_user()`` to verify it, and returns an
    ``AuthenticatedUser`` with the user's ID and token.

    Raises 401 if the token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        # Verify the JWT against Supabase Auth
        client = get_supabase_client()
        user_response = client.auth.get_user(token)
        user = user_response.user
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return AuthenticatedUser(user_id=user.id, access_token=token)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Auth verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
