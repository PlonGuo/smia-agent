"""Import all collectors to trigger self-registration."""

from . import (  # noqa: F401
    arxiv_collector,
    bluesky_collector,
    currents_collector,
    github_collector,
    hackernews_collector,
    rss_collector,
)
