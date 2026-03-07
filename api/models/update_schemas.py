"""Schemas for the deploy-success notification feature."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    id: str
    message: str
    author: str
    url: str


class UpdateSummary(BaseModel):
    headline: str = Field(max_length=80)
    summary: str = Field(max_length=500)
    highlights: list[str] = Field(max_length=5)


class NotifyUpdateRequest(BaseModel):
    commits: list[CommitInfo] = Field(default_factory=list)
    manual_summary: UpdateSummary | None = None
