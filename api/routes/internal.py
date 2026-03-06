"""Internal webhook endpoints — secured by x-internal-secret header."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

from core.config import settings
from services.database import get_all_user_emails
from services.email_service import send_update_notification

router = APIRouter(prefix="/api/internal", tags=["internal"])


@router.post("/notify-update")
async def notify_update(request: Request, body: dict):
    """Receive push event data from GitHub Actions and email all users."""
    t0 = time.time()
    print("[INTERNAL/NOTIFY-UPDATE] Received request")

    secret = request.headers.get("x-internal-secret", "")
    if secret != settings.internal_secret:
        print("[INTERNAL/NOTIFY-UPDATE] Auth failed: secret mismatch")
        raise HTTPException(status_code=403, detail="Unauthorized")

    commits = body.get("commits", [])
    if not commits:
        print("[INTERNAL/NOTIFY-UPDATE] No commits provided")
        return {"status": "skipped", "reason": "no commits"}

    emails = get_all_user_emails()
    print(f"[INTERNAL/NOTIFY-UPDATE] Found {len(emails)} user emails")

    if not emails:
        return {"status": "skipped", "reason": "no users found"}

    sent = send_update_notification(commits, emails)
    elapsed_ms = int((time.time() - t0) * 1000)
    print(f"[INTERNAL/NOTIFY-UPDATE] Sent {sent}/{len(emails)} emails in {elapsed_ms}ms")

    return {
        "status": "ok",
        "emails_sent": sent,
        "total_users": len(emails),
        "elapsed_ms": elapsed_ms,
    }
