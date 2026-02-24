"""Feedback/voting endpoints for digest items."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthenticatedUser, get_current_user
from models.digest_schemas import FeedbackCreate
from services.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("/vote", status_code=status.HTTP_201_CREATED)
async def vote(
    body: FeedbackCreate,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Vote on a digest item (upvote / downvote). Upserts per user+item."""
    client = get_supabase_client(user.access_token)

    resp = (
        client.table("digest_feedback")
        .upsert({
            "user_id": user.user_id,
            "digest_id": body.digest_id,
            "item_url": body.item_url,
            "vote": body.vote,
        }, on_conflict="user_id,item_url")
        .execute()
    )
    return {"feedback": resp.data[0] if resp.data else {}}


@router.get("/digest/{digest_id}")
async def get_digest_feedback(
    digest_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get user's votes for a specific digest."""
    client = get_supabase_client(user.access_token)

    resp = (
        client.table("digest_feedback")
        .select("*")
        .eq("user_id", user.user_id)
        .eq("digest_id", digest_id)
        .execute()
    )
    return {"votes": resp.data}
