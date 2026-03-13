"""POST /api/analyze — run multi-source analysis."""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from langfuse import observe

from core.auth import AuthenticatedUser, get_current_user
from core.rate_limit import DAILY_LIMIT, check_rate_limit
from models.schemas import AnalyzeRequest, AnalyzeResponse, QuotaResponse
from services.agent import analyze_topic
from services.database import save_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyze"])


@observe(name="save_report_to_supabase")
def _save_report_observed(report_data: dict, user_id: str, access_token: str) -> dict:
    return save_report(report_data=report_data, user_id=user_id, access_token=access_token)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    body: AnalyzeRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> AnalyzeResponse:
    """Analyze a topic across Reddit, YouTube, and Amazon.

    Requires a valid Supabase JWT in the Authorization header.
    Supports time_range (day/week/month/year) and force_refresh params.
    """
    # Rate limit check
    allowed, remaining = check_rate_limit(user.user_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. You can perform 5 analyses per day.",
        )

    try:
        report, cached = await analyze_topic(
            query=body.query,
            user_id=user.user_id,
            source="web",
            time_range=body.time_range,
            force_refresh=body.force_refresh,
        )

        # Persist to Supabase (skip if cached — already saved previously)
        if not cached:
            try:
                saved = _save_report_observed(
                    report_data=report.model_dump(exclude={"id", "created_at"}),
                    user_id=user.user_id,
                    access_token=user.access_token,
                )
                report.id = saved.get("id")
                raw_ts = saved.get("created_at")
                if raw_ts:
                    report.created_at = datetime.fromisoformat(raw_ts)
            except Exception as save_exc:
                logger.error("Failed to save report: %s", save_exc)

        post_remaining = remaining if cached else remaining - 1
        return AnalyzeResponse(report=report, cached=cached, remaining=post_remaining)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Analysis failed for query '%s': %s\n%s", body.query, exc, tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Please try again later.",
        ) from exc


def _next_utc_midnight() -> str:
    """Return ISO timestamp for the start of the next UTC day."""
    now = datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return tomorrow.isoformat()


@router.get("/analyze/quota", response_model=QuotaResponse)
async def get_quota(
    user: AuthenticatedUser = Depends(get_current_user),
) -> QuotaResponse:
    """Return the user's remaining daily analysis quota."""
    _, remaining = check_rate_limit(user.user_id)
    return QuotaResponse(
        daily_limit=DAILY_LIMIT,
        remaining=remaining,
        resets_at=_next_utc_midnight(),
    )
