"""AI Daily Report endpoints — digest lifecycle + access control."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status

from core.auth import AuthenticatedUser, get_current_user
from core.config import settings
from models.digest_schemas import AccessRequestCreate
from services.database import (
    get_digest_access_status,
    get_all_admin_emails,
    get_supabase_client,
)
from services.digest_service import claim_or_get_digest, run_analysis_phase, run_collectors_phase
from services.email_service import send_access_request_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-daily-report", tags=["ai-daily-report"])


# ---------------------------------------------------------------------------
# Digest lifecycle
# ---------------------------------------------------------------------------


@router.get("/today")
async def get_today_digest(
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Main endpoint: check permission, claim/return digest.

    Returns FAST. If we claimed the lock, the collectors pipeline runs as a
    BackgroundTask so we don't block the HTTP response.
    """
    access = get_digest_access_status(user.user_id, user.access_token)
    if access not in ("admin", "approved"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access status: {access}",
        )

    result = claim_or_get_digest(user.user_id, user.access_token)

    if result.get("claimed"):
        background_tasks.add_task(run_collectors_phase, result["digest_id"])

    return result


@router.get("/status")
async def get_access_status(
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Return current user's digest access status."""
    access = get_digest_access_status(user.user_id, user.access_token)
    return {"access": access}


@router.get("/list")
async def list_digests(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List past digests (last 30 days). Requires digest access."""
    access = get_digest_access_status(user.user_id, user.access_token)
    if access not in ("admin", "approved"):
        raise HTTPException(status_code=403, detail=f"Access status: {access}")

    client = get_supabase_client()
    offset = (page - 1) * per_page

    data_resp = (
        client.table("daily_digests")
        .select("id, digest_date, status, executive_summary, total_items, category_counts, created_at")
        .eq("status", "completed")
        .order("digest_date", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    count_resp = (
        client.table("daily_digests")
        .select("id", count="exact")
        .eq("status", "completed")
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
        if expiry < datetime.now(timezone.utc):
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
    """Get specific digest by ID. Requires digest access."""
    access = get_digest_access_status(user.user_id, user.access_token)
    if access not in ("admin", "approved"):
        raise HTTPException(status_code=403, detail=f"Access status: {access}")

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
    """Submit a digest access request."""
    # Check if already authorized
    access = get_digest_access_status(user.user_id, user.access_token)
    if access in ("admin", "approved"):
        return {"status": "already_authorized", "access": access}

    if access == "pending":
        return {"status": "already_pending"}

    client = get_supabase_client()

    # Create request
    client.table("digest_access_requests").insert({
        "user_id": user.user_id,
        "email": body.email,
        "reason": body.reason,
        "status": "pending",
    }).execute()

    # Notify admins
    admin_emails = get_all_admin_emails()
    for email in admin_emails:
        try:
            send_access_request_notification(email, body.email, body.reason)
        except Exception as exc:
            logger.error("Failed to email admin %s: %s", email, exc)

    return {"status": "pending"}


# ---------------------------------------------------------------------------
# Share tokens
# ---------------------------------------------------------------------------


@router.post("/share")
async def create_share_token(
    digest_id: str = Query(...),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Generate a shareable link for a digest."""
    access = get_digest_access_status(user.user_id, user.access_token)
    if access not in ("admin", "approved"):
        raise HTTPException(status_code=403, detail=f"Access status: {access}")

    token = uuid.uuid4().hex[:16]
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    client = get_supabase_client()
    client.table("digest_share_tokens").insert({
        "digest_id": digest_id,
        "token": token,
        "created_by": user.user_id,
        "expires_at": expires_at,
    }).execute()

    app_url = (settings.app_url or "").rstrip("/")
    share_url = f"{app_url}/ai-daily-report/shared/{token}"

    return {"token": token, "url": share_url, "expires_at": expires_at}


# ---------------------------------------------------------------------------
# Internal: Phase 2 trigger (two-phase pipeline)
# ---------------------------------------------------------------------------


@router.post("/internal/analyze")
async def internal_analyze(
    request: Request,
    body: dict,
    background_tasks: BackgroundTasks,
):
    """Internal endpoint: triggered by Phase 1 to start Phase 2 (LLM analysis).

    Secured by x-internal-secret header. Runs Phase 2 in BackgroundTask
    so this serverless function gets its own fresh 60s budget.
    """
    secret = request.headers.get("x-internal-secret", "")
    if secret != settings.internal_secret:
        raise HTTPException(status_code=403, detail="Unauthorized")

    digest_id = body.get("digest_id")
    if not digest_id:
        raise HTTPException(status_code=400, detail="Missing digest_id")

    background_tasks.add_task(run_analysis_phase, digest_id)
    return {"status": "accepted", "digest_id": digest_id}


@router.post("/internal/collect")
async def internal_collect(
    request: Request,
    body: dict,
    background_tasks: BackgroundTasks,
):
    """Internal endpoint: trigger Phase 1 (collectors) in a fresh function invocation.

    Used by Telegram /digest command to avoid running collectors inline
    in the webhook handler (which would hit the 60s Vercel timeout).
    """
    secret = request.headers.get("x-internal-secret", "")
    if secret != settings.internal_secret:
        raise HTTPException(status_code=403, detail="Unauthorized")

    digest_id = body.get("digest_id")
    if not digest_id:
        raise HTTPException(status_code=400, detail="Missing digest_id")

    background_tasks.add_task(run_collectors_phase, digest_id)
    return {"status": "accepted", "digest_id": digest_id}
