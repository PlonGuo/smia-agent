"""Tests for collector_factory module."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestLazyImport:
    def test_lazy_import_returns_class(self):
        from services.collector_factory import _lazy_import

        cls = _lazy_import("arxiv_collector", "ArxivCollector")
        assert isinstance(cls, type)
        assert cls.__name__ == "ArxivCollector"


class TestLazyRss:
    def test_lazy_rss_returns_collector(self):
        from services.collector_factory import _lazy_rss
        from services.collectors.rss_collector import RssCollector

        collector = _lazy_rss({"rss_config": "test.json"})
        assert isinstance(collector, RssCollector)
        assert collector.name == "rss"

    def test_lazy_rss_named_returns_collector(self):
        from services.collector_factory import _lazy_rss_named
        from services.collectors.rss_collector import RssCollector

        collector = _lazy_rss_named("news_rss", "news_feeds.json")
        assert isinstance(collector, RssCollector)
        assert collector.name == "news_rss"


class TestLazyGuardian:
    def test_lazy_guardian_with_config(self):
        from services.collector_factory import _lazy_guardian
        from services.collectors.guardian_collector import GuardianCollector

        collector = _lazy_guardian({"guardian_sections": ["tech"], "guardian_keywords": ["AI"]})
        assert isinstance(collector, GuardianCollector)
        assert collector._sections == ["tech"]
        assert collector._keywords == ["AI"]

    def test_lazy_guardian_defaults(self):
        from services.collector_factory import _lazy_guardian
        from services.collectors.guardian_collector import GuardianCollector

        collector = _lazy_guardian({})
        assert isinstance(collector, GuardianCollector)
        assert collector._sections == ["world"]
        assert collector._keywords is None


class TestGetCollectorsForTopic:
    def test_get_collectors_for_topic_ai(self):
        from services.collector_factory import get_collectors_for_topic

        collectors = get_collectors_for_topic("ai")
        assert len(collectors) > 0

    def test_get_collectors_for_topic_geopolitics(self):
        from services.collector_factory import get_collectors_for_topic
        from services.collectors.guardian_collector import GuardianCollector

        collectors = get_collectors_for_topic("geopolitics")
        assert len(collectors) > 0
        # Geopolitics topic includes guardian
        collector_types = [type(c) for c in collectors]
        assert GuardianCollector in collector_types

    def test_unknown_collector_logs_warning(self):
        from services.collector_factory import get_collectors_for_topic

        with patch(
            "services.collector_factory.DIGEST_TOPICS",
            {"test": {"collectors": ["unknown_collector"]}},
        ):
            with patch("services.collector_factory.logger") as mock_logger:
                result = get_collectors_for_topic("test")
                mock_logger.warning.assert_called_once()
                assert result == []
