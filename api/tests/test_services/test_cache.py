"""Unit tests for the cache service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.cache import (
    _FETCH_LIMITS,
    _FETCH_TTL,
    _ANALYSIS_TTL,
    get_fetch_limits,
    normalize_query,
)


# ---------------------------------------------------------------------------
# normalize_query
# ---------------------------------------------------------------------------


class TestNormalizeQuery:
    def test_lowercase(self):
        assert normalize_query("Plaud AI") == "plaud ai"

    def test_strip_whitespace(self):
        assert normalize_query("  plaud  ") == "plaud"

    def test_collapse_multiple_spaces(self):
        assert normalize_query("plaud   ai   note") == "plaud ai note"

    def test_mixed_case_and_spaces(self):
        assert normalize_query("  PLAUD   AI   Note  ") == "plaud ai note"

    def test_empty_string(self):
        assert normalize_query("") == ""

    def test_single_word(self):
        assert normalize_query("iphone") == "iphone"

    def test_already_normalized(self):
        assert normalize_query("plaud ai") == "plaud ai"

    def test_tabs_and_newlines(self):
        assert normalize_query("plaud\tai\nnote") == "plaud ai note"


# ---------------------------------------------------------------------------
# get_fetch_limits
# ---------------------------------------------------------------------------


class TestGetFetchLimits:
    def test_day_limits(self):
        limits = get_fetch_limits("day")
        assert limits["reddit"] == 8
        assert limits["youtube"] == 8
        assert limits["amazon"] == 2

    def test_week_limits(self):
        limits = get_fetch_limits("week")
        assert limits["reddit"] == 15
        assert limits["youtube"] == 15
        assert limits["amazon"] == 3

    def test_month_limits(self):
        limits = get_fetch_limits("month")
        assert limits["reddit"] == 25
        assert limits["youtube"] == 25
        assert limits["amazon"] == 5

    def test_year_limits(self):
        limits = get_fetch_limits("year")
        assert limits["reddit"] == 35
        assert limits["youtube"] == 30
        assert limits["amazon"] == 6

    def test_unknown_falls_back_to_week(self):
        limits = get_fetch_limits("invalid")
        assert limits == get_fetch_limits("week")

    def test_month_bigger_than_week(self):
        week = get_fetch_limits("week")
        month = get_fetch_limits("month")
        for source in ["reddit", "youtube", "amazon"]:
            assert month[source] >= week[source]

    def test_year_bigger_than_month(self):
        month = get_fetch_limits("month")
        year = get_fetch_limits("year")
        for source in ["reddit", "youtube", "amazon"]:
            assert year[source] >= month[source]


# ---------------------------------------------------------------------------
# TTL config sanity checks
# ---------------------------------------------------------------------------


class TestTTLConfig:
    def test_fetch_ttl_day_shorter_than_year(self):
        assert _FETCH_TTL["day"] < _FETCH_TTL["year"]

    def test_analysis_ttl_day_shorter_than_year(self):
        assert _ANALYSIS_TTL["day"] < _ANALYSIS_TTL["year"]

    def test_all_time_ranges_have_fetch_ttl(self):
        for tr in ["day", "week", "month", "year"]:
            assert tr in _FETCH_TTL

    def test_all_time_ranges_have_analysis_ttl(self):
        for tr in ["day", "week", "month", "year"]:
            assert tr in _ANALYSIS_TTL

    def test_all_time_ranges_have_limits(self):
        for tr in ["day", "week", "month", "year"]:
            assert tr in _FETCH_LIMITS
            for source in ["reddit", "youtube", "amazon"]:
                assert source in _FETCH_LIMITS[tr]


# ---------------------------------------------------------------------------
# Cache read/write (mocking Supabase)
# ---------------------------------------------------------------------------


class TestGetCachedFetch:
    def test_returns_data_on_cache_hit(self):
        mock_response = MagicMock()
        mock_response.data = {"data": [{"title": "Cached post"}]}

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gt.return_value.maybe_single.return_value.execute.return_value = mock_response

        with patch("services.cache.get_supabase_client", return_value=mock_client):
            from services.cache import get_cached_fetch
            result = get_cached_fetch("plaud", "week", "reddit")

        assert result == [{"title": "Cached post"}]

    def test_returns_none_on_cache_miss(self):
        mock_response = MagicMock()
        mock_response.data = None

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gt.return_value.maybe_single.return_value.execute.return_value = mock_response

        with patch("services.cache.get_supabase_client", return_value=mock_client):
            from services.cache import get_cached_fetch
            result = get_cached_fetch("plaud", "week", "reddit")

        assert result is None

    def test_returns_none_on_exception(self):
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("DB error")

        with patch("services.cache.get_supabase_client", return_value=mock_client):
            from services.cache import get_cached_fetch
            result = get_cached_fetch("plaud", "week", "reddit")

        assert result is None


class TestSetCachedFetch:
    def test_upserts_data(self):
        mock_client = MagicMock()

        with patch("services.cache.get_supabase_client", return_value=mock_client):
            from services.cache import set_cached_fetch
            set_cached_fetch("plaud", "week", "reddit", [{"title": "Post"}])

        mock_client.table.assert_called_once_with("fetch_cache")
        mock_client.table.return_value.upsert.assert_called_once()
        upsert_args = mock_client.table.return_value.upsert.call_args
        payload = upsert_args[0][0]
        assert payload["query_normalized"] == "plaud"
        assert payload["time_range"] == "week"
        assert payload["source"] == "reddit"
        assert payload["item_count"] == 1

    def test_handles_exception_gracefully(self):
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("DB error")

        with patch("services.cache.get_supabase_client", return_value=mock_client):
            from services.cache import set_cached_fetch
            # Should not raise
            set_cached_fetch("plaud", "week", "reddit", [])


class TestGetCachedAnalysis:
    def test_returns_report_on_hit(self):
        report = {"topic": "plaud", "sentiment": "Positive"}
        mock_response = MagicMock()
        mock_response.data = {"report": report}

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.maybe_single.return_value.execute.return_value = mock_response

        with patch("services.cache.get_supabase_client", return_value=mock_client):
            from services.cache import get_cached_analysis
            result = get_cached_analysis("plaud", "week")

        assert result == report

    def test_returns_none_on_miss(self):
        mock_response = MagicMock()
        mock_response.data = None

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.maybe_single.return_value.execute.return_value = mock_response

        with patch("services.cache.get_supabase_client", return_value=mock_client):
            from services.cache import get_cached_analysis
            result = get_cached_analysis("plaud", "week")

        assert result is None


class TestSetCachedAnalysis:
    def test_upserts_report(self):
        mock_client = MagicMock()
        report = {"topic": "plaud", "sentiment": "Positive"}

        with patch("services.cache.get_supabase_client", return_value=mock_client):
            from services.cache import set_cached_analysis
            set_cached_analysis("plaud", "week", report)

        mock_client.table.assert_called_once_with("analysis_cache")
        mock_client.table.return_value.upsert.assert_called_once()
