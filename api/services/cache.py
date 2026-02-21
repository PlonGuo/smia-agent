"""Two-tier caching: raw crawler data (per-source) + analysis results.

Cache keys:
  - Fetch cache: (normalized_query, time_range, source)
  - Analysis cache: (normalized_query, time_range)

Uses Supabase PostgreSQL via service-role client (no RLS).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from services.database import get_supabase_client

logger = logging.getLogger(__name__)

TimeRange = Literal["day", "week", "month", "year"]

# ---------------------------------------------------------------------------
# TTLs (generous — single-user app, "Regenerate" button available)
# ---------------------------------------------------------------------------

_FETCH_TTL: dict[str, timedelta] = {
    "day": timedelta(hours=12),
    "week": timedelta(hours=24),
    "month": timedelta(days=3),
    "year": timedelta(days=7),
}

_ANALYSIS_TTL: dict[str, timedelta] = {
    "day": timedelta(hours=12),
    "week": timedelta(hours=24),
    "month": timedelta(days=3),
    "year": timedelta(days=7),
}

# ---------------------------------------------------------------------------
# Fetch limits per source, scaled by time range
# ---------------------------------------------------------------------------

_FETCH_LIMITS: dict[str, dict[str, int]] = {
    "day": {"reddit": 8, "youtube": 8, "amazon": 2},
    "week": {"reddit": 15, "youtube": 15, "amazon": 3},
    "month": {"reddit": 25, "youtube": 25, "amazon": 5},
    "year": {"reddit": 35, "youtube": 30, "amazon": 6},
}


def get_fetch_limits(time_range: str) -> dict[str, int]:
    """Return per-source fetch limits for the given time range."""
    return _FETCH_LIMITS.get(time_range, _FETCH_LIMITS["week"])


# ---------------------------------------------------------------------------
# Query normalization
# ---------------------------------------------------------------------------

_MULTI_SPACE = re.compile(r"\s+")


def normalize_query(query: str) -> str:
    """Normalize query for cache key: lowercase, strip, collapse whitespace."""
    return _MULTI_SPACE.sub(" ", query.strip().lower())


# ---------------------------------------------------------------------------
# Fetch cache (Tier 1 — raw crawler output per source)
# ---------------------------------------------------------------------------


def get_cached_fetch(
    query: str, time_range: str, source: str
) -> list[dict[str, Any]] | None:
    """Return cached crawler data if available and not expired."""
    norm = normalize_query(query)
    client = get_supabase_client()  # service-role
    now = datetime.now(timezone.utc).isoformat()

    try:
        response = (
            client.table("fetch_cache")
            .select("data")
            .eq("query_normalized", norm)
            .eq("time_range", time_range)
            .eq("source", source)
            .gt("expires_at", now)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            logger.info("Cache MISS [fetch] %s/%s/%s", source, time_range, norm)
            return None

        logger.info("Cache HIT [fetch] %s/%s/%s", source, time_range, norm)
        return response.data["data"]
    except Exception as exc:
        logger.warning("Fetch cache read failed: %s", exc)
        return None


def set_cached_fetch(
    query: str, time_range: str, source: str, data: list[dict[str, Any]]
) -> None:
    """Store crawler output in cache. Upserts on conflict."""
    norm = normalize_query(query)
    ttl = _FETCH_TTL.get(time_range, _FETCH_TTL["week"])
    expires_at = (datetime.now(timezone.utc) + ttl).isoformat()
    client = get_supabase_client()  # service-role

    try:
        client.table("fetch_cache").upsert(
            {
                "query_normalized": norm,
                "time_range": time_range,
                "source": source,
                "data": data,
                "item_count": len(data),
                "expires_at": expires_at,
            },
            on_conflict="query_normalized,time_range,source",
        ).execute()
        logger.info(
            "Cache SET [fetch] %s/%s/%s (%d items, TTL %s)",
            source, time_range, norm, len(data), ttl,
        )
    except Exception as exc:
        logger.warning("Fetch cache write failed: %s", exc)


# ---------------------------------------------------------------------------
# Analysis cache (Tier 2 — full TrendReport)
# ---------------------------------------------------------------------------


def get_cached_analysis(query: str, time_range: str) -> dict[str, Any] | None:
    """Return cached analysis report if available and not expired.

    Returns the raw dict (not a TrendReport instance) to avoid import cycles.
    The caller is responsible for constructing the TrendReport.
    """
    norm = normalize_query(query)
    client = get_supabase_client()  # service-role
    now = datetime.now(timezone.utc).isoformat()

    try:
        response = (
            client.table("analysis_cache")
            .select("report")
            .eq("query_normalized", norm)
            .eq("time_range", time_range)
            .gt("expires_at", now)
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            logger.info("Cache MISS [analysis] %s/%s", time_range, norm)
            return None

        logger.info("Cache HIT [analysis] %s/%s", time_range, norm)
        return response.data["report"]
    except Exception as exc:
        logger.warning("Analysis cache read failed: %s", exc)
        return None


def set_cached_analysis(
    query: str, time_range: str, report: dict[str, Any]
) -> None:
    """Store analysis report in cache. Upserts on conflict."""
    norm = normalize_query(query)
    ttl = _ANALYSIS_TTL.get(time_range, _ANALYSIS_TTL["week"])
    expires_at = (datetime.now(timezone.utc) + ttl).isoformat()
    client = get_supabase_client()  # service-role

    try:
        client.table("analysis_cache").upsert(
            {
                "query_normalized": norm,
                "time_range": time_range,
                "report": report,
                "expires_at": expires_at,
            },
            on_conflict="query_normalized,time_range",
        ).execute()
        logger.info(
            "Cache SET [analysis] %s/%s (TTL %s)", time_range, norm, ttl,
        )
    except Exception as exc:
        logger.warning("Analysis cache write failed: %s", exc)
