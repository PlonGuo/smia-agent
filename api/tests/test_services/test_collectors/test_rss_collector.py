"""Tests for RSS/blog collector."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from time import struct_time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def _make_feed_entry(title="Test Post", published_parsed=None, summary="<p>Test content</p>"):
    """Create a mock feedparser entry."""
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "title": title,
        "link": "https://blog.example.com/post-1",
        "author": "Author",
    }.get(key, default)
    entry.title = title
    entry.link = "https://blog.example.com/post-1"
    entry.summary = summary
    entry.author = "Author"

    if published_parsed is None:
        # Recent time
        entry.published_parsed = struct_time((2026, 2, 24, 12, 0, 0, 0, 55, 0))
    else:
        entry.published_parsed = published_parsed
    entry.updated_parsed = None
    return entry


def _make_parsed_feed(entries=None, bozo=False):
    """Create a mock feedparser result."""
    feed = MagicMock()
    feed.entries = [_make_feed_entry()] if entries is None else entries
    feed.bozo = bozo
    return feed


class TestRssCollector:
    @pytest.mark.asyncio
    async def test_returns_items(self):
        feeds_config = {"feeds": [{"name": "Test Blog", "url": "https://blog.example.com/feed"}]}
        parsed = _make_parsed_feed([_make_feed_entry()])

        with patch("services.collectors.rss_collector._config_path") as mock_path, \
             patch("builtins.open", create=True) as mock_open, \
             patch("json.load", return_value=feeds_config), \
             patch("services.collectors.rss_collector.feedparser.parse", return_value=parsed):
            from services.collectors.rss_collector import RssCollector
            items = await RssCollector().collect()

            assert len(items) == 1
            assert items[0].source == "rss"
            assert items[0].title == "Test Post"

    @pytest.mark.asyncio
    async def test_strips_html_from_summary(self):
        entry = _make_feed_entry(summary="<p>Hello <b>world</b></p>")
        feeds_config = {"feeds": [{"name": "Test", "url": "https://example.com/feed"}]}
        parsed = _make_parsed_feed([entry])

        with patch("builtins.open", create=True), \
             patch("json.load", return_value=feeds_config), \
             patch("services.collectors.rss_collector.feedparser.parse", return_value=parsed):
            from services.collectors.rss_collector import RssCollector
            items = await RssCollector().collect()

            assert "<" not in items[0].snippet
            assert "Hello world" in items[0].snippet

    @pytest.mark.asyncio
    async def test_old_entries_filtered(self):
        # Entry from 2020 — should be filtered out
        old_time = struct_time((2020, 1, 1, 0, 0, 0, 0, 1, 0))
        entry = _make_feed_entry(published_parsed=old_time)
        feeds_config = {"feeds": [{"name": "Test", "url": "https://example.com/feed"}]}
        parsed = _make_parsed_feed([entry])

        with patch("builtins.open", create=True), \
             patch("json.load", return_value=feeds_config), \
             patch("services.collectors.rss_collector.feedparser.parse", return_value=parsed):
            from services.collectors.rss_collector import RssCollector
            items = await RssCollector().collect()
            assert items == []

    @pytest.mark.asyncio
    async def test_malformed_feed_skipped(self):
        feeds_config = {"feeds": [{"name": "Bad Feed", "url": "https://bad.com/feed"}]}
        parsed = _make_parsed_feed(entries=[], bozo=True)

        with patch("builtins.open", create=True), \
             patch("json.load", return_value=feeds_config), \
             patch("services.collectors.rss_collector.feedparser.parse", return_value=parsed):
            from services.collectors.rss_collector import RssCollector
            items = await RssCollector().collect()
            assert items == []

    @pytest.mark.asyncio
    async def test_empty_feeds_config(self):
        with patch("builtins.open", create=True), \
             patch("json.load", return_value={"feeds": []}):
            from services.collectors.rss_collector import RssCollector
            items = await RssCollector().collect()
            assert items == []
