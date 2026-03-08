"""Factory for instantiating topic-specific collectors."""

import logging

from config.digest_topics import DIGEST_TOPICS

logger = logging.getLogger(__name__)

# Simple collectors: no config needed, just instantiate
SIMPLE_COLLECTORS = {
    "arxiv": lambda: _lazy_import("arxiv_collector", "ArxivCollector")(),
    "github": lambda: _lazy_import("github_collector", "GithubCollector")(),
    "bluesky": lambda: _lazy_import("bluesky_collector", "BlueskyCollector")(),
    "hackernews": lambda: _lazy_import("hackernews_collector", "HackernewsCollector")(),
    "currents": lambda: _lazy_import("currents_collector", "CurrentsCollector")(),
}

# Parameterized collectors: need topic config dict
PARAMETERIZED_COLLECTORS = {
    "rss": lambda cfg: _lazy_rss(cfg),
    "news_rss": lambda cfg: _lazy_rss_named("news_rss", "news_rss_feeds.json"),
    "climate_rss": lambda cfg: _lazy_rss_named("climate_rss", "climate_rss_feeds.json"),
    "health_rss": lambda cfg: _lazy_rss_named("health_rss", "health_rss_feeds.json"),
    "guardian": lambda cfg: _lazy_guardian(cfg),
}


def _lazy_import(module_name: str, class_name: str):
    """Lazily import a collector class from services.collectors."""
    import importlib
    mod = importlib.import_module(f"services.collectors.{module_name}")
    return getattr(mod, class_name)


def _lazy_rss(cfg: dict):
    """Instantiate RssCollector with topic-specific config file."""
    from services.collectors.rss_collector import RssCollector
    return RssCollector(name="rss", config_file=cfg.get("rss_config", "rss_feeds.json"))


def _lazy_rss_named(name: str, config_file: str):
    """Instantiate RssCollector with explicit name and config file."""
    from services.collectors.rss_collector import RssCollector
    return RssCollector(name=name, config_file=config_file)


def _lazy_guardian(cfg: dict):
    """Instantiate GuardianCollector with topic-specific sections and keywords."""
    from services.collectors.guardian_collector import GuardianCollector
    return GuardianCollector(
        name="guardian",
        sections=cfg.get("guardian_sections", ["world"]),
        keywords=cfg.get("guardian_keywords"),
    )


def get_collectors_for_topic(topic: str) -> list:
    """Return a list of collector instances for the given topic.

    Raises KeyError if topic is not defined in DIGEST_TOPICS.
    """
    topic_cfg = DIGEST_TOPICS[topic]
    collectors = []
    for name in topic_cfg["collectors"]:
        if name in SIMPLE_COLLECTORS:
            collectors.append(SIMPLE_COLLECTORS[name]())
        elif name in PARAMETERIZED_COLLECTORS:
            collectors.append(PARAMETERIZED_COLLECTORS[name](topic_cfg))
        else:
            logger.warning("Unknown collector: %s", name)
    return collectors
