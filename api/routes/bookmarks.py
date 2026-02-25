"""Bookmark endpoints for digest items."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.auth import AuthenticatedUser, get_current_user
from models.digest_schemas import BookmarkCreate
from services.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


@router.get("/")
async def list_bookmarks(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List user's bookmarked digest items."""
    client = get_supabase_client(user.access_token)
    offset = (page - 1) * per_page

    resp = (
        client.table("digest_bookmarks")
        .select("*")
        .eq("user_id", user.user_id)
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return {"bookmarks": resp.data}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    body: BookmarkCreate,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Bookmark a digest item."""
    client = get_supabase_client(user.access_token)

    resp = (
        client.table("digest_bookmarks")
        .upsert({
            "user_id": user.user_id,
            "digest_id": body.digest_id,
            "item_url": body.item_url,
            "item_title": body.item_title,
        }, on_conflict="user_id,item_url")
        .execute()
    )
    return {"bookmark": resp.data[0] if resp.data else {}}


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Remove a bookmark."""
    client = get_supabase_client(user.access_token)
    client.table("digest_bookmarks").delete().eq("id", bookmark_id).execute()
