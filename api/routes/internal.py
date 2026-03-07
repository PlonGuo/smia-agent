"""Internal webhook endpoints — secured by x-internal-secret header."""

from __future__ import annotations

import hmac
import time
import traceback

from fastapi import APIRouter, HTTPException, Request

from core.config import settings
from models.update_schemas import NotifyUpdateRequest, UpdateSummary
from services.database import get_all_user_emails
from services.email_service import _filter_commits, send_update_notification
from services.update_summarizer import summarize_commits

router = APIRouter(prefix="/api/internal", tags=["internal"])


@router.post("/notify-update")
async def notify_update(request: Request, body: NotifyUpdateRequest):
    """Receive deployment data from GitHub Actions and email all users."""
    t0 = time.time()
    print("[INTERNAL/NOTIFY-UPDATE] Received request")

    if not settings.internal_secret:
        print("[INTERNAL/NOTIFY-UPDATE] Auth failed: internal_secret not configured")
        raise HTTPException(status_code=503, detail="Not configured")

    secret = request.headers.get("x-internal-secret", "").strip()
    if not hmac.compare_digest(secret.encode(), settings.internal_secret.strip().encode()):
        print("[INTERNAL/NOTIFY-UPDATE] Auth failed: secret mismatch")
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Manual summary mode: use provided content directly
    if body.manual_summary:
        summary = body.manual_summary
        print(f"[INTERNAL/NOTIFY-UPDATE] Using manual summary: {summary.headline}")
    else:
        commits_raw = [c.model_dump() for c in body.commits]
        if not commits_raw:
            print("[INTERNAL/NOTIFY-UPDATE] No commits provided")
            return {"status": "skipped", "reason": "no commits"}

        # Filter noise commits
        meaningful = _filter_commits(commits_raw)
        if not meaningful:
            print("[INTERNAL/NOTIFY-UPDATE] All commits filtered as noise")
            return {"status": "skipped", "reason": "no meaningful commits"}

        # Generate AI summary with fallback
        try:
            summary = await summarize_commits(meaningful)
            print(f"[INTERNAL/NOTIFY-UPDATE] LLM summary: {summary.headline}")
        except Exception as exc:
            print(f"[INTERNAL/NOTIFY-UPDATE] LLM failed, using fallback: {exc}")
            print(f"[INTERNAL/NOTIFY-UPDATE] {traceback.format_exc()[-500:]}")
            first_msg = meaningful[0].get("message", "").split("\n", 1)[0]
            summary = UpdateSummary(
                headline=first_msg[:80],
                summary=f"The platform has been updated with {len(meaningful)} changes.",
                highlights=[
                    c.get("message", "").split("\n", 1)[0]
                    for c in meaningful[:5]
                ],
            )

    emails = get_all_user_emails()
    print(f"[INTERNAL/NOTIFY-UPDATE] Found {len(emails)} user emails")

    if not emails:
        return {"status": "skipped", "reason": "no users found"}

    sent = send_update_notification(summary, emails)
    elapsed_ms = int((time.time() - t0) * 1000)
    print(f"[INTERNAL/NOTIFY-UPDATE] Sent {sent}/{len(emails)} emails in {elapsed_ms}ms")

    return {
        "status": "ok",
        "emails_sent": sent,
        "total_users": len(emails),
        "elapsed_ms": elapsed_ms,
    }
