"""Topic configuration for multi-topic daily digests."""

DIGEST_TOPICS = {
    "ai": {
        "display_name": "AI Intelligence",
        "collectors": ["arxiv", "github", "rss", "bluesky"],
        "categories": [
            "Breakthrough", "Research", "Tooling", "Open Source",
            "Infrastructure", "Product", "Policy", "Safety", "Other",
        ],
        "rss_config": "rss_feeds.json",
    },
    "geopolitics": {
        "display_name": "Geopolitics & Conflict",
        "collectors": ["guardian", "news_rss", "currents", "hackernews"],
        "categories": [
            "Conflict & Security", "Diplomacy", "Trade & Sanctions",
            "Political Change", "Regional Tensions", "Other",
        ],
        "rss_config": "news_rss_feeds.json",
        "guardian_sections": ["world", "politics"],
        "guardian_keywords": ["conflict", "diplomacy", "sanctions", "war"],
    },
    "climate": {
        "display_name": "Climate & Environment",
        "collectors": ["guardian", "climate_rss", "currents"],
        "categories": [
            "Policy & Regulation", "Extreme Weather", "Energy Transition",
            "Research & Data", "Activism & Society", "Other",
        ],
        "rss_config": "climate_rss_feeds.json",
        "guardian_sections": ["environment"],
        "guardian_keywords": ["climate", "energy", "emissions", "renewable"],
    },
    "health": {
        "display_name": "Health & Medical",
        "collectors": ["health_rss", "currents"],
        "categories": [
            "Breakthrough", "Disease & Outbreak", "Drug & Treatment",
            "Public Health Policy", "Research", "Other",
        ],
        "rss_config": "health_rss_feeds.json",
    },
}
