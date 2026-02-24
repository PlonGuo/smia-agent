"""Tests for Pydantic models in api/models/digest_schemas.py."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from models.digest_schemas import (
    RawCollectorItem,
    DigestItem,
    DailyDigestLLMOutput,
    DailyDigestDB,
    AccessRequestCreate,
    AccessRequestResponse,
    DigestStatusResponse,
    BookmarkCreate,
    FeedbackCreate,
)


class TestRawCollectorItem:
    def test_valid_full(self):
        item = RawCollectorItem(
            title="Test Paper",
            url="https://arxiv.org/abs/2401.00001",
            source="arxiv",
            snippet="A test paper about AI",
            author="John Doe",
            published_at=datetime.now(timezone.utc),
            extra={"stars": 100},
        )
        assert item.source == "arxiv"
        assert item.extra["stars"] == 100

    def test_valid_minimal(self):
        item = RawCollectorItem(
            title="Test", url="https://example.com", source="github"
        )
        assert item.snippet is None
        assert item.author is None
        assert item.published_at is None
        assert item.extra == {}

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            RawCollectorItem(title="Test")


class TestDigestItem:
    def test_valid(self):
        item = DigestItem(
            title="New AI Model",
            url="https://example.com",
            source="arxiv",
            category="Breakthrough",
            importance=5,
            why_it_matters="This changes everything in the field",
        )
        assert item.category == "Breakthrough"
        assert item.importance == 5
        assert item.also_on == []

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            DigestItem(
                title="Test",
                url="https://example.com",
                source="arxiv",
                category="InvalidCategory",
                importance=3,
                why_it_matters="Some reason here for this item",
            )

    def test_importance_out_of_range(self):
        with pytest.raises(ValidationError):
            DigestItem(
                title="Test",
                url="https://example.com",
                source="arxiv",
                category="Research",
                importance=6,
                why_it_matters="Some reason here for this item",
            )

    def test_importance_zero(self):
        with pytest.raises(ValidationError):
            DigestItem(
                title="Test",
                url="https://example.com",
                source="arxiv",
                category="Research",
                importance=0,
                why_it_matters="Some reason here for this item",
            )

    def test_why_it_matters_too_short(self):
        with pytest.raises(ValidationError):
            DigestItem(
                title="Test",
                url="https://example.com",
                source="arxiv",
                category="Research",
                importance=3,
                why_it_matters="Short",
            )

    def test_also_on_populated(self):
        item = DigestItem(
            title="Test",
            url="https://example.com",
            source="arxiv",
            category="Research",
            importance=3,
            why_it_matters="This is important because of reasons",
            also_on=["github", "rss"],
        )
        assert item.also_on == ["github", "rss"]


class TestDailyDigestLLMOutput:
    def _make_digest_item(self, **kwargs):
        defaults = dict(
            title="Test",
            url="https://example.com",
            source="arxiv",
            category="Research",
            importance=3,
            why_it_matters="This is important because of reasons",
        )
        defaults.update(kwargs)
        return DigestItem(**defaults)

    def test_valid(self):
        output = DailyDigestLLMOutput(
            executive_summary="Today saw major breakthroughs in AI.",
            items=[self._make_digest_item()],
            top_highlights=["Highlight 1", "Highlight 2", "Highlight 3"],
            trending_keywords=["AI", "LLM", "scaling"],
            category_counts={"Research": 1},
            source_counts={"arxiv": 1},
        )
        assert len(output.items) == 1
        assert len(output.top_highlights) == 3

    def test_too_few_highlights(self):
        with pytest.raises(ValidationError):
            DailyDigestLLMOutput(
                executive_summary="Summary",
                items=[self._make_digest_item()],
                top_highlights=["Only one"],
                trending_keywords=["AI"],
                category_counts={"Research": 1},
                source_counts={"arxiv": 1},
            )

    def test_too_many_highlights(self):
        with pytest.raises(ValidationError):
            DailyDigestLLMOutput(
                executive_summary="Summary",
                items=[self._make_digest_item()],
                top_highlights=["H1", "H2", "H3", "H4", "H5", "H6"],
                trending_keywords=["AI"],
                category_counts={"Research": 1},
                source_counts={"arxiv": 1},
            )


class TestDailyDigestDB:
    def test_inherits_llm_output(self):
        item = DigestItem(
            title="Test",
            url="https://example.com",
            source="arxiv",
            category="Research",
            importance=3,
            why_it_matters="This is important because of reasons",
        )
        now = datetime.now(timezone.utc)
        db = DailyDigestDB(
            executive_summary="Summary",
            items=[item],
            top_highlights=["H1", "H2", "H3"],
            trending_keywords=["AI"],
            category_counts={"Research": 1},
            source_counts={"arxiv": 1},
            id="test-id",
            digest_date="2026-02-24",
            status="completed",
            source_health={"arxiv": "ok", "github": "ok"},
            total_items=1,
            model_used="gpt-4.1",
            processing_time_seconds=30,
            created_at=now,
            updated_at=now,
        )
        assert db.status == "completed"
        assert db.model_used == "gpt-4.1"
        assert db.executive_summary == "Summary"


class TestAccessRequestCreate:
    def test_valid(self):
        req = AccessRequestCreate(email="user@test.com", reason="I need access to view AI daily reports for my research.")
        assert req.email == "user@test.com"
        assert len(req.reason) > 10

    def test_too_short(self):
        # reason defaults to "" which is valid now (optional reason)
        req = AccessRequestCreate(email="user@test.com", reason="")
        assert req.reason == ""

    def test_too_long(self):
        with pytest.raises(ValidationError):
            AccessRequestCreate(email="user@test.com", reason="x" * 501)


class TestAccessRequestResponse:
    def test_valid(self):
        resp = AccessRequestResponse(
            id="test-id",
            email="user@example.com",
            reason="I need access",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        assert resp.status == "pending"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            AccessRequestResponse(
                id="test-id",
                email="user@example.com",
                reason="I need access",
                status="unknown",
                created_at=datetime.now(timezone.utc),
            )


class TestDigestStatusResponse:
    def test_completed(self):
        resp = DigestStatusResponse(
            status="completed",
            digest_id="test-id",
            digest={"executive_summary": "Test"},
        )
        assert resp.status == "completed"

    def test_not_found(self):
        resp = DigestStatusResponse(status="not_found")
        assert resp.digest_id is None
        assert resp.digest is None


class TestBookmarkCreate:
    def test_valid(self):
        bm = BookmarkCreate(
            digest_id="test-id",
            item_url="https://arxiv.org/abs/2401.00001",
            item_title="Test Paper",
        )
        assert bm.item_title == "Test Paper"

    def test_without_title(self):
        bm = BookmarkCreate(digest_id="test-id", item_url="https://example.com")
        assert bm.item_title is None


class TestFeedbackCreate:
    def test_thumbs_up(self):
        fb = FeedbackCreate(digest_id="test-id", vote=1)
        assert fb.vote == 1
        assert fb.item_url is None

    def test_thumbs_down_with_item(self):
        fb = FeedbackCreate(
            digest_id="test-id", item_url="https://example.com", vote=-1
        )
        assert fb.vote == -1

    def test_invalid_vote(self):
        with pytest.raises(ValidationError):
            FeedbackCreate(digest_id="test-id", vote=0)
