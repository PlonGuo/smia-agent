"""POST /api/analyze — run multi-source analysis."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthenticatedUser, get_current_user
from models.schemas import AnalyzeRequest, AnalyzeResponse
from services.agent import analyze_topic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    body: AnalyzeRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> AnalyzeResponse:
    """Analyze a topic across Reddit, YouTube, and Amazon.

    Requires a valid Supabase JWT in the Authorization header.
    """
    try:
        report = await analyze_topic(
            query=body.query,
            user_id=user.user_id,
            source="web",
        )
        return AnalyzeResponse(report=report)
    except Exception as exc:
        logger.error("Analysis failed for query '%s': %s", body.query, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        ) from exc
