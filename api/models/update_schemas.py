"""Schemas for the deploy-success notification feature."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CommitInfo(BaseModel):
    id: str
    message: str
    author: str = "unknown"
    url: str = ""

    @field_validator("author", "url", "message", mode="before")
    @classmethod
    def coerce_none(cls, v: object) -> str:
        return v if v is not None else ""


class UpdateSummary(BaseModel):
    headline: str = Field(max_length=80)
    summary: str = Field(max_length=500)
    highlights: list[str] = Field(max_length=5)


class NotifyUpdateRequest(BaseModel):
    commits: list[CommitInfo] = Field(default_factory=list)
    manual_summary: UpdateSummary | None = None
