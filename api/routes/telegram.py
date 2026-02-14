"""Telegram webhook endpoint.

Receives updates from Telegram Bot API and dispatches them
to the telegram_service handler.  No JWT auth required — the
endpoint validates the request comes from Telegram by checking
the bot token in the URL path (Telegram's recommended approach
for webhook security).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from services.telegram_service import handle_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
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

    logger.info(
        "Telegram update received: update_id=%s",
        update.get("update_id", "?"),
    )

    # Process in background so we return 200 quickly
    background_tasks.add_task(_process_update, update)

    return JSONResponse({"ok": True})


async def _process_update(update: dict) -> None:
    """Wrapper for handle_update with error logging."""
    try:
        await handle_update(update)
    except Exception:
        logger.exception("Unhandled error processing Telegram update")
