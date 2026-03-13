"""Rate limiting for analysis endpoints.

Uses Supabase to count recent analyses per user, making it
compatible with serverless environments (no shared in-memory state).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from services.database import get_supabase_client

logger = logging.getLogger(__name__)

DAILY_LIMIT = 5  # analyses per day per user (shared across web + telegram)


def check_rate_limit(user_id: str) -> tuple[bool, int]:
    """Check if a user has exceeded their daily analysis rate limit.

    Counts all analyses created since the start of the current UTC day.
    Returns (allowed, remaining) where allowed is True if the user
    can proceed, and remaining is how many analyses they have left.
    """
    start_of_day = (
        datetime.now(UTC)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat()
    )

    try:
        client = get_supabase_client()  # service-role
        response = (
            client.table("analysis_reports")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", start_of_day)
            .execute()
        )
        count = response.count or 0
    except Exception as exc:
        logger.error("Rate limit check failed: %s", exc)
        # Fail open — don't block users if the check itself fails
        return True, DAILY_LIMIT

    remaining = max(0, DAILY_LIMIT - count)
    return count < DAILY_LIMIT, remaining
