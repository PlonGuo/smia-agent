"""Tests for Pydantic models in api/models/schemas.py."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BindCodeResponse,
    BindConfirmRequest,
    ReportsListResponse,
    TopDiscussion,
    TrendReport,
)
from tests.conftest import make_trend_report_data


class TestTopDiscussion:
    def test_valid(self):
        d = TopDiscussion(
            title="Test", url="https://example.com", source="reddit"
        )
        assert d.source == "reddit"

    def test_optional_fields(self):
        d = TopDiscussion(
            title="Test", url="https://example.com", source="youtube"
        )
        assert d.score is None
        assert d.snippet is None

    def test_invalid_source(self):
        with pytest.raises(ValidationError):
            TopDiscussion(
                title="Test", url="https://example.com", source="twitter"
            )


class TestTrendReport:
    def test_valid_report(self):
        data = make_trend_report_data()
        report = TrendReport(**data)
        assert report.topic == "Test Topic"
        assert report.sentiment == "Positive"
        assert report.sentiment_score == 0.75

    def test_sentiment_score_bounds(self):
        # Score = 0 is valid
        data = make_trend_report_data(sentiment_score=0.0)
        report = TrendReport(**data)
        assert report.sentiment_score == 0.0

        # Score = 1 is valid
        data = make_trend_report_data(sentiment_score=1.0)
        report = TrendReport(**data)
        assert report.sentiment_score == 1.0

        # Score > 1 is invalid
        with pytest.raises(ValidationError):
            TrendReport(**make_trend_report_data(sentiment_score=1.5))

        # Score < 0 is invalid
        with pytest.raises(ValidationError):
            TrendReport(**make_trend_report_data(sentiment_score=-0.1))

    def test_invalid_sentiment(self):
        with pytest.raises(ValidationError):
            TrendReport(**make_trend_report_data(sentiment="Mixed"))

    def test_summary_too_short(self):
        with pytest.raises(ValidationError):
            TrendReport(**make_trend_report_data(summary="Too short"))

    def test_too_few_insights(self):
        with pytest.raises(ValidationError):
            TrendReport(**make_trend_report_data(key_insights=["one", "two"]))

    def test_too_few_keywords(self):
        with pytest.raises(ValidationError):
            TrendReport(
                **make_trend_report_data(keywords=["a", "b", "c", "d"])
            )

    def test_metadata_optional(self):
        data = make_trend_report_data()
        report = TrendReport(**data)
        assert report.id is None
        assert report.user_id is None
        assert report.created_at is None

    def test_metadata_populated(self):
        now = datetime.now(timezone.utc)
        data = make_trend_report_data(
            id="abc-123",
            user_id="user-456",
            query="test query",
            source="web",
            processing_time_seconds=60,
            langfuse_trace_id="trace-789",
            token_usage={"prompt": 100, "completion": 50, "total": 150},
            created_at=now,
        )
        report = TrendReport(**data)
        assert report.id == "abc-123"
        assert report.source == "web"
        assert report.token_usage["total"] == 150


class TestAnalyzeRequest:
    def test_valid(self):
        req = AnalyzeRequest(query="What is the sentiment on Plaud Note?")
        assert req.query == "What is the sentiment on Plaud Note?"

    def test_too_short(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(query="ab")

    def test_too_long(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(query="x" * 201)

    def test_empty(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(query="")


class TestAnalyzeResponse:
    def test_valid(self):
        data = make_trend_report_data()
        resp = AnalyzeResponse(report=TrendReport(**data))
        assert resp.message == "Analysis complete"


class TestReportsListResponse:
    def test_valid(self):
        resp = ReportsListResponse(reports=[], total=0, page=1, per_page=20)
        assert resp.total == 0


class TestBindCodeResponse:
    def test_valid(self):
        now = datetime.now(timezone.utc)
        resp = BindCodeResponse(bind_code="123456", expires_at=now)
        assert resp.bind_code == "123456"


class TestBindConfirmRequest:
    def test_valid(self):
        req = BindConfirmRequest(telegram_user_id=123456789, bind_code="123456")
        assert req.telegram_user_id == 123456789

    def test_code_too_short(self):
        with pytest.raises(ValidationError):
            BindConfirmRequest(telegram_user_id=123, bind_code="12345")

    def test_code_too_long(self):
        with pytest.raises(ValidationError):
            BindConfirmRequest(telegram_user_id=123, bind_code="1234567")
