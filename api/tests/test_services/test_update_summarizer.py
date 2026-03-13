"""Tests for update_summarizer service."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from models.update_schemas import UpdateSummary
from services.update_summarizer import _validate_summary


def _make_summary(**kwargs) -> UpdateSummary:
    defaults = dict(
        headline="New features added",
        summary="We improved the platform with several enhancements.",
        highlights=["Added dashboard", "Fixed login bug"],
    )
    defaults.update(kwargs)
    return UpdateSummary(**defaults)


class TestValidateSummary:
    def test_validate_summary_passes_clean(self):
        summary = _make_summary()
        result = _validate_summary(summary)
        assert result is summary

    def test_validate_summary_rejects_url_in_headline(self):
        summary = _make_summary(headline="Check https://example.com now")
        with pytest.raises(ValueError, match="URL"):
            _validate_summary(summary)

    def test_validate_summary_rejects_url_in_summary(self):
        summary = _make_summary(
            summary="Visit http://example.com for details."
        )
        with pytest.raises(ValueError, match="URL"):
            _validate_summary(summary)

    def test_validate_summary_rejects_url_in_highlight(self):
        summary = _make_summary(highlights=["See https://example.com for more"])
        with pytest.raises(ValueError, match="URL"):
            _validate_summary(summary)

    def test_validate_summary_rejects_html(self):
        summary = _make_summary(headline="<b>bold</b> headline")
        with pytest.raises(ValueError, match="HTML"):
            _validate_summary(summary)

    def test_validate_summary_rejects_html_in_summary(self):
        summary = _make_summary(summary="This is <strong>important</strong>.")
        with pytest.raises(ValueError, match="HTML"):
            _validate_summary(summary)


class TestSummarizeCommits:
    async def test_summarize_commits_calls_agent(self):
        from services.update_summarizer import summarize_commits

        expected_output = _make_summary()
        mock_result = MagicMock()
        mock_result.output = expected_output

        with patch("services.update_summarizer._summarizer.run", new=AsyncMock(return_value=mock_result)):
            commits = [
                {"message": "feat: add dashboard"},
                {"message": "fix: correct login bug"},
            ]
            result = await summarize_commits(commits)
            assert result == expected_output
