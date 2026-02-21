"""POST /api/analyze — run multi-source analysis."""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from langfuse import observe

from core.auth import AuthenticatedUser, get_current_user
from core.rate_limit import check_rate_limit
from models.schemas import AnalyzeRequest, AnalyzeResponse
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
    allowed, remaining = check_rate_limit(user.user_id, source="web")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. You can perform 100 analyses per hour.",
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
                report.created_at = saved.get("created_at")
            except Exception as save_exc:
                logger.error("Failed to save report: %s", save_exc)

        return AnalyzeResponse(report=report, cached=cached)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Analysis failed for query '%s': %s\n%s", body.query, exc, tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {type(exc).__name__}: {exc}",
        ) from exc
