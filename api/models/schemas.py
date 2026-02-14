"""Pydantic models for SmIA API."""

from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class TopDiscussion(BaseModel):
    title: str
    url: str
    source: Literal["reddit", "youtube", "amazon"]
    score: int | None = None
    snippet: str | None = None


class TrendReport(BaseModel):
    topic: str = Field(description="Main topic analyzed")
    sentiment: Literal["Positive", "Negative", "Neutral"]
    sentiment_score: float = Field(ge=0, le=1)
    summary: str = Field(min_length=50, max_length=500)
    key_insights: list[str] = Field(min_length=3, max_length=5)
    top_discussions: list[TopDiscussion] = Field(max_length=15)
    keywords: list[str] = Field(min_length=5, max_length=10)
    source_breakdown: dict[str, int]
    charts_data: dict = Field(default_factory=dict)

    # Metadata
    id: str | None = None
    user_id: str | None = None
    query: str | None = None
    source: Literal["web", "telegram"] | None = None
    processing_time_seconds: int | None = None
    langfuse_trace_id: str | None = None
    token_usage: dict | None = None
    created_at: datetime | None = None


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=3, max_length=200)


class AnalyzeResponse(BaseModel):
    report: TrendReport
    message: str = "Analysis complete"


class ReportsListResponse(BaseModel):
    reports: list[TrendReport]
    total: int
    page: int
    per_page: int


class BindCodeResponse(BaseModel):
    bind_code: str
    expires_at: datetime


class BindConfirmRequest(BaseModel):
    telegram_user_id: int
    bind_code: str = Field(min_length=6, max_length=6)
