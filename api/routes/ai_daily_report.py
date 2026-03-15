"""AI Daily Report endpoints — digest lifecycle + access control."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from config.digest_topics import DIGEST_TOPICS
from core.auth import AuthenticatedUser, get_current_user
from core.config import settings
from models.digest_schemas import AccessRequestCreate
from services.database import get_supabase_client
from services.digest_service import claim_or_get_digest, run_digest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-daily-report", tags=["ai-daily-report"])

# Background task tracking — prevents GC and logs errors
_background_tasks: set[asyncio.Task] = set()


def _task_done(task: asyncio.Task) -> None:
    _background_tasks.discard(task)
    if not task.cancelled() and task.exception():
        logger.error("Background digest failed: %s", task.exception(), exc_info=task.exception())


# ---------------------------------------------------------------------------
# Digest lifecycle
# ---------------------------------------------------------------------------


@router.get("/topics")
async def list_topics():
    """Return available digest topics."""
    return {
        "topics": [
            {"key": key, "display_name": cfg["display_name"]}
            for key, cfg in DIGEST_TOPICS.items()
        ]
    }


@router.get("/today")
async def get_today_digest(
    topic: str = Query("ai"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Main endpoint: check permission, claim/return digest.

    Returns FAST. If we claimed the lock, the digest pipeline runs as a
    background asyncio task so we don't block the HTTP response.
    """
    if topic not in DIGEST_TOPICS:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {topic}")

    result = claim_or_get_digest(user.user_id, user.access_token, topic=topic)

    if result.get("claimed"):
        task = asyncio.create_task(run_digest(result["digest_id"], topic=topic))
        _background_tasks.add(task)
        task.add_done_callback(_task_done)

    return result


@router.get("/status")
async def get_access_status(
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Return current user's digest access status.

    With open access, all authenticated users are treated as approved.
    Kept for backward compatibility with frontend.
    """
    return {"access": "approved"}


@router.get("/list")
async def list_digests(
    topic: str = Query("ai"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List past digests (last 30 days), filtered by topic."""
    client = get_supabase_client()
    offset = (page - 1) * per_page

    data_resp = (
        client.table("daily_digests")
        .select("id, digest_date, topic, status, executive_summary, total_items, category_counts, created_at")
        .eq("status", "completed")
        .eq("topic", topic)
        .order("digest_date", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    count_resp = (
        client.table("daily_digests")
        .select("id", count="exact")
        .eq("status", "completed")
        .eq("topic", topic)
        .execute()
    )
    return {
        "digests": data_resp.data,
        "total": count_resp.count or 0,
        "page": page,
        "per_page": per_page,
    }


@router.get("/shared/{token}")
async def get_shared_digest(token: str):
    """Public endpoint: get digest by share token (no auth required)."""
    client = get_supabase_client()

    token_row = (
        client.table("digest_share_tokens")
        .select("digest_id, expires_at")
        .eq("token", token)
        .maybe_single()
        .execute()
    )
    if token_row is None or not token_row.data:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")

    # Check expiry
    expires_at = token_row.data.get("expires_at")
    if expires_at:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expiry < datetime.now(UTC):
            raise HTTPException(status_code=410, detail="Share link has expired")

    digest = (
        client.table("daily_digests")
        .select("*")
        .eq("id", token_row.data["digest_id"])
        .single()
        .execute()
    )
    return {"digest": digest.data}


@router.get("/{digest_id}")
async def get_digest(
    digest_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get specific digest by ID."""
    client = get_supabase_client()
    resp = (
        client.table("daily_digests")
        .select("*")
        .eq("id", digest_id)
        .maybe_single()
        .execute()
    )
    if resp is None or not resp.data:
        raise HTTPException(status_code=404, detail="Digest not found")

    return {"digest": resp.data}


# ---------------------------------------------------------------------------
# Access requests
# ---------------------------------------------------------------------------


@router.post("/access-request", status_code=status.HTTP_201_CREATED)
async def request_access(
    body: AccessRequestCreate,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Submit a digest access request.

    With open access, all authenticated users are already authorized.
    Kept for backward compatibility.
    """
    return {"status": "already_authorized", "access": "approved"}


# ---------------------------------------------------------------------------
# Share tokens
# ---------------------------------------------------------------------------


@router.post("/share")
async def create_share_token(
    digest_id: str = Query(...),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Generate a shareable link for a digest."""
    token = uuid.uuid4().hex[:16]
    expires_at = (datetime.now(UTC) + timedelta(hours=24)).isoformat()

    client = get_supabase_client()
    client.table("digest_share_tokens").insert({
        "digest_id": digest_id,
        "token": token,
        "created_by": user.user_id,
        "expires_at": expires_at,
    }).execute()

    share_url = f"{settings.frontend_url}/ai-daily-report/shared/{token}"

    return {"token": token, "url": share_url, "expires_at": expires_at}
