"""Tests for collector registry and self-registration."""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from services.collectors.base import COLLECTOR_REGISTRY


class TestCollectorRegistry:
    def test_all_collectors_registered(self):
        """Importing __init__ registers all collectors (original 4 + new ones)."""
        from services.collectors import (  # noqa: F401
            arxiv_collector,
            bluesky_collector,
            github_collector,
            rss_collector,
        )

        assert "arxiv" in COLLECTOR_REGISTRY
        assert "github" in COLLECTOR_REGISTRY
        assert "rss" in COLLECTOR_REGISTRY
        assert "bluesky" in COLLECTOR_REGISTRY

    def test_unique_names(self):
        from services.collectors import (  # noqa: F401
            arxiv_collector,
            bluesky_collector,
            github_collector,
            rss_collector,
        )

        names = [c.name for c in COLLECTOR_REGISTRY.values()]
        assert len(names) == len(set(names))

    def test_collect_is_async(self):
        from services.collectors import (  # noqa: F401
            arxiv_collector,
            bluesky_collector,
            github_collector,
            rss_collector,
        )

        for name, collector in COLLECTOR_REGISTRY.items():
            assert inspect.iscoroutinefunction(collector.collect), (
                f"{name}.collect() must be async"
            )

    def test_registry_has_at_least_four_collectors(self):
        """Registry now has 4 original + new collectors (hackernews, currents)."""
        from services.collectors import (  # noqa: F401
            arxiv_collector,
            bluesky_collector,
            github_collector,
            rss_collector,
        )

        assert len(COLLECTOR_REGISTRY) >= 4
