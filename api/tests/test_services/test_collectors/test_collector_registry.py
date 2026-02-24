"""Tests for collector registry and self-registration."""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from services.collectors.base import COLLECTOR_REGISTRY, Collector


class TestCollectorRegistry:
    def test_all_collectors_registered(self):
        """Importing __init__ registers all 4 collectors."""
        from services.collectors import arxiv_collector, github_collector, rss_collector, bluesky_collector  # noqa: F401

        assert "arxiv" in COLLECTOR_REGISTRY
        assert "github" in COLLECTOR_REGISTRY
        assert "rss" in COLLECTOR_REGISTRY
        assert "bluesky" in COLLECTOR_REGISTRY

    def test_unique_names(self):
        from services.collectors import arxiv_collector, github_collector, rss_collector, bluesky_collector  # noqa: F401

        names = [c.name for c in COLLECTOR_REGISTRY.values()]
        assert len(names) == len(set(names))

    def test_collect_is_async(self):
        from services.collectors import arxiv_collector, github_collector, rss_collector, bluesky_collector  # noqa: F401

        for name, collector in COLLECTOR_REGISTRY.items():
            assert inspect.iscoroutinefunction(collector.collect), (
                f"{name}.collect() must be async"
            )

    def test_registry_has_four_collectors(self):
        from services.collectors import arxiv_collector, github_collector, rss_collector, bluesky_collector  # noqa: F401

        assert len(COLLECTOR_REGISTRY) == 4
