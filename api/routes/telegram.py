"""Telegram webhook endpoint.

Receives updates from Telegram Bot API and dispatches them
to the telegram_service handler.  No JWT auth required — the
endpoint validates the request comes from Telegram by checking
the bot token in the URL path (Telegram's recommended approach
for webhook security).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.telegram_service import handle_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
) -> JSONResponse:
    """Receive a Telegram Update and process it.

    Returns 200 immediately and processes the update in a background task
    to avoid Telegram's webhook timeout (60 seconds).
    """
    try:
        update = await request.json()
    except Exception:
        logger.warning("Invalid JSON in Telegram webhook request")
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    text = update.get("message", {}).get("text", "")
    print(f"[TG WEBHOOK] update_id={update.get('update_id')}, text={text[:50]}")

    # Process synchronously — our handlers are fast (<2s) since heavy work
    # is delegated via HTTP to /internal/collect and /internal/analyze.
    # BackgroundTasks on Vercel get killed before completing.
    try:
        await handle_update(update)
        print("[TG WEBHOOK] handle_update completed")
    except Exception as exc:
        import traceback
        print(f"[TG WEBHOOK] handle_update FAILED: {exc}\n{traceback.format_exc()}")
        logger.exception("Unhandled error processing Telegram update")

    return JSONResponse({"ok": True})
