"""Auth & binding endpoints."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthenticatedUser, get_current_user
from models.schemas import BindCodeResponse, BindConfirmRequest
from services.database import (
    complete_binding,
    lookup_bind_code,
    save_bind_code,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["auth"])

BIND_CODE_LENGTH = 6
BIND_CODE_EXPIRY_MINUTES = 10


def _generate_bind_code() -> str:
    """Generate a random 6-character alphanumeric bind code."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No ambiguous chars (0/O, 1/I)
    return "".join(secrets.choice(alphabet) for _ in range(BIND_CODE_LENGTH))


@router.get("/bind/code", response_model=BindCodeResponse)
async def generate_bind_code(
    user: AuthenticatedUser = Depends(get_current_user),
) -> BindCodeResponse:
    """Generate a one-time bind code for Telegram account linking.

    The code expires after 10 minutes. The user sends this code
    to the Telegram bot via ``/bind <code>`` to link accounts.
    """
    code = _generate_bind_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=BIND_CODE_EXPIRY_MINUTES)
    expires_iso = expires_at.isoformat()

    save_bind_code(
        user_id=user.user_id,
        bind_code=code,
        expires_at=expires_iso,
        access_token=user.access_token,
    )

    return BindCodeResponse(bind_code=code, expires_at=expires_at)


@router.post("/bind/confirm", status_code=status.HTTP_200_OK)
async def confirm_binding(body: BindConfirmRequest) -> dict:
    """Confirm a Telegram binding (called by the Telegram bot webhook).

    This endpoint does NOT require user auth — it's called server-side
    by the Telegram webhook handler using the service-role key.
    """
    binding = lookup_bind_code(body.bind_code)
    if binding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired bind code",
        )

    try:
        result = complete_binding(
            bind_code=body.bind_code,
            telegram_user_id=body.telegram_user_id,
        )
        return {"status": "bound", "user_id": result.get("user_id")}
    except Exception as exc:
        logger.error("Binding confirmation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete binding",
        ) from exc


