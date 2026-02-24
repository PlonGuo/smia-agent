"""Admin endpoints for managing digest access requests and admins."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.auth import AuthenticatedUser, get_current_user
from services.database import (
    get_supabase_client,
    is_admin,
)
from services.email_service import send_approval_email, send_rejection_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(user: AuthenticatedUser) -> AuthenticatedUser:
    """Raise 403 if the user is not an admin."""
    if not is_admin(user.user_id, user.access_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ---------------------------------------------------------------------------
# Access requests
# ---------------------------------------------------------------------------

@router.get("/requests")
async def list_access_requests(
    request_status: str | None = Query(None, alias="status"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List digest access requests (admin only)."""
    _require_admin(user)
    client = get_supabase_client()  # service role to see all requests

    query = client.table("digest_access_requests").select("*")
    if request_status:
        query = query.eq("status", request_status)
    query = query.order("created_at", desc=True)

    response = query.execute()
    return {"requests": response.data}


@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Approve a digest access request."""
    _require_admin(user)
    client = get_supabase_client()  # service role

    # Fetch the request
    req = (
        client.table("digest_access_requests")
        .select("*")
        .eq("id", request_id)
        .maybe_single()
        .execute()
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    req_data = req.data
    if req_data["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")

    # Update request status
    client.table("digest_access_requests").update({
        "status": "approved",
        "reviewed_by": user.user_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", request_id).execute()

    # Add to authorized users
    client.table("digest_authorized_users").upsert({
        "user_id": req_data["user_id"],
        "email": req_data["email"],
        "approved_by": user.user_id,
    }, on_conflict="user_id").execute()

    # Send approval email
    send_approval_email(req_data["email"])

    return {"status": "approved", "request_id": request_id}


@router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: str,
    reason: str | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Reject a digest access request."""
    _require_admin(user)
    client = get_supabase_client()  # service role

    req = (
        client.table("digest_access_requests")
        .select("*")
        .eq("id", request_id)
        .maybe_single()
        .execute()
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    req_data = req.data
    if req_data["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")

    client.table("digest_access_requests").update({
        "status": "rejected",
        "rejection_reason": reason,
        "reviewed_by": user.user_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", request_id).execute()

    send_rejection_email(req_data["email"], reason)

    return {"status": "rejected", "request_id": request_id}


# ---------------------------------------------------------------------------
# Admin management
# ---------------------------------------------------------------------------

@router.get("/admins")
async def list_admins(
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List all admins."""
    _require_admin(user)
    client = get_supabase_client()  # service role
    response = client.table("admins").select("*").order("created_at").execute()
    return {"admins": response.data}


@router.post("/admins", status_code=status.HTTP_201_CREATED)
async def add_admin(
    email: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Add a new admin by email."""
    _require_admin(user)
    client = get_supabase_client()  # service role

    try:
        client.rpc("seed_admin", {"p_email": email}).execute()
    except Exception as exc:
        logger.error("Failed to add admin %s: %s", email, exc)
        raise HTTPException(status_code=400, detail="Failed to add admin. User may not exist.")

    # Verify it was actually created
    result = (
        client.table("admins")
        .select("*")
        .eq("email", email)
        .maybe_single()
        .execute()
    )
    if result is None:
        raise HTTPException(status_code=400, detail="User not found in auth system")

    return {"admin": result.data}


@router.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_admin(
    admin_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Remove an admin."""
    _require_admin(user)
    client = get_supabase_client()  # service role

    # Prevent removing yourself
    admin_row = (
        client.table("admins")
        .select("user_id")
        .eq("id", admin_id)
        .maybe_single()
        .execute()
    )
    if admin_row is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    if admin_row.data["user_id"] == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself as admin")

    client.table("admins").delete().eq("id", admin_id).execute()
