"""Pydantic models for AI Daily Report feature."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- Collector models ---

class RawCollectorItem(BaseModel):
    title: str
    url: str
    source: str  # "arxiv", "github", "rss", "bluesky"
    snippet: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    extra: dict = Field(default_factory=dict)


# --- Digest output models (LLM structured output) ---

CategoryType = Literal[
    "Breakthrough", "Research", "Tooling", "Open Source",
    "Infrastructure", "Product", "Policy", "Safety", "Other"
]


class DigestItem(BaseModel):
    title: str
    url: str
    source: str
    category: CategoryType
    importance: int = Field(ge=1, le=5)
    why_it_matters: str = Field(min_length=10, max_length=200)
    also_on: list[str] = Field(default_factory=list)


# (I9) Separate LLM output from full DB row
class DailyDigestLLMOutput(BaseModel):
    """Structured output from PydanticAI agent — what the LLM generates."""
    executive_summary: str
    items: list[DigestItem]
    top_highlights: list[str] = Field(min_length=3, max_length=5)
    trending_keywords: list[str]
    category_counts: dict[str, int]
    source_counts: dict[str, int]


class DailyDigestDB(DailyDigestLLMOutput):
    """Full DB row — LLM output + metadata set by orchestrator."""
    id: str
    digest_date: str
    status: str
    source_health: dict[str, str]
    total_items: int
    model_used: str
    processing_time_seconds: int
    langfuse_trace_id: str | None = None
    token_usage: dict | None = None
    prompt_version: str | None = None
    created_at: datetime
    updated_at: datetime


# --- API request/response models ---

class AccessRequestCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


class AccessRequestResponse(BaseModel):
    id: str
    email: str
    reason: str
    status: Literal["pending", "approved", "rejected"]
    rejection_reason: str | None = None
    created_at: datetime


class DigestStatusResponse(BaseModel):
    status: Literal["collecting", "analyzing", "completed", "failed", "not_found"]
    digest_id: str | None = None
    digest: dict | None = None


class BookmarkCreate(BaseModel):
    digest_id: str
    item_url: str
    item_title: str | None = None


class FeedbackCreate(BaseModel):
    digest_id: str
    item_url: str | None = None
    vote: Literal[1, -1]
