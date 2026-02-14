"""Reports CRUD endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.auth import AuthenticatedUser, get_current_user
from models.schemas import ReportsListResponse, TrendReport
from services.database import delete_report, get_report_by_id, get_reports

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports", response_model=ReportsListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sentiment: str | None = Query(None),
    source: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    search: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ReportsListResponse:
    """Return paginated, filtered analysis reports for the authenticated user."""
    reports, total = get_reports(
        user_id=user.user_id,
        access_token=user.access_token,
        page=page,
        per_page=per_page,
        sentiment=sentiment,
        source=source,
        from_date=from_date,
        to_date=to_date,
        search=search,
    )
    return ReportsListResponse(
        reports=reports,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/reports/{report_id}", response_model=TrendReport)
async def get_report(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> TrendReport:
    """Fetch a single report by ID."""
    report = get_report_by_id(
        report_id=report_id,
        user_id=user.user_id,
        access_token=user.access_token,
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return report


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_report(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Delete a report."""
    deleted = delete_report(
        report_id=report_id,
        user_id=user.user_id,
        access_token=user.access_token,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or already deleted",
        )
