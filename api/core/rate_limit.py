"""Rate limiting for analysis endpoints.

Uses Supabase to count recent analyses per user, making it
compatible with serverless environments (no shared in-memory state).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from core.config import settings
from services.database import get_supabase_client

logger = logging.getLogger(__name__)

WEB_RATE_LIMIT = 100  # analyses per hour for web users
TELEGRAM_RATE_LIMIT = 10  # analyses per hour for Telegram users


def check_rate_limit(user_id: str, source: str = "web") -> tuple[bool, int]:
    """Check if a user has exceeded their hourly analysis rate limit.

    Returns (allowed, remaining) where allowed is True if the user
    can proceed, and remaining is how many analyses they have left.
    """
    limit = TELEGRAM_RATE_LIMIT if source == "telegram" else WEB_RATE_LIMIT
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    try:
        client = get_supabase_client()  # service-role
        response = (
            client.table("analysis_reports")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", one_hour_ago)
            .execute()
        )
        count = response.count or 0
    except Exception as exc:
        logger.error("Rate limit check failed: %s", exc)
        # Fail open — don't block users if the check itself fails
        return True, limit

    remaining = max(0, limit - count)
    return count < limit, remaining
