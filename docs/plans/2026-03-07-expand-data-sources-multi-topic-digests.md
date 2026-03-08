# Plan: Expand Data Sources + Multi-Topic Digests

## Context

SmIA currently has 3 Analyze tools (Reddit, YouTube, Amazon) and 4 Digest collectors (arXiv, GitHub, RSS blogs, Bluesky) — all focused on AI/tech. The user wants to:
1. **Analyze**: Add more data sources so PydanticAI can intelligently choose which to query based on user topic
2. **Digest**: Expand from 1 AI-only daily digest to 4 independent topic digests (AI, Geopolitics, Climate, Health)

Discussed and decided in previous session (2026-03-07). Fly.io migration is complete. This is the next feature.

**Branch**: `expand-data-sources` (off `development`)

---

## Part A: New Analyze Tools

### A1: New Crawler Functions

**File**: `api/services/crawler.py` — add 5 new async functions

| Function | Source | API | Notes |
|----------|--------|-----|-------|
| `fetch_hackernews(query, limit=15)` | HN Algolia API | `http://hn.algolia.com/api/v1/search` | Free, no rate limit. Returns stories + comments. |
| `fetch_devto(query, limit=10)` | Dev.to API | `https://dev.to/api/articles` | Free, no key needed. Filter by tag. Has `body_markdown` + comments API. |
| `fetch_news_rss(query, feeds, limit=10)` | RSS feeds | feedparser | Reuse pattern from `rss_collector.py` (run_in_executor). Pass feed list. |
| `fetch_stackexchange(query, limit=10)` | Stack Exchange API | `https://api.stackexchange.com/2.3/search` | 300/day without key, 10k/day with free key. Filter by `site=stackoverflow` |
| `fetch_guardian(query, limit=10, section=None)` | Guardian Content API | `https://content.guardianapis.com/search` | 5000/day free, 12/sec. Returns full article text via `show-fields=bodyText`. API key: `GUARDIAN_API_KEY` |

Each returns `list[dict]` matching existing tool patterns (title, url, body/content, comments, score).

### A2: News RSS Feed Config

**File**: `api/config/news_rss_feeds.json` (NEW)

```json
{
  "feeds": [
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Reuters World", "url": "https://rsshub.app/reuters/world"},
    {"name": "AP News", "url": "https://rsshub.app/apnews/topics/world-news"},
    {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml"},
    {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"}
  ]
}
```

RSSHub public instance (`rsshub.app`) used for Reuters and AP News which don't have native RSS.

### A3: Tool Design — One Tool Per Source, Rich Descriptions

**Design principle**: Each data source = one PydanticAI tool. The tool's docstring tells the LLM **what the source is**, **what topics it's best for**, and **when to use it**. PydanticAI uses these docstrings as tool descriptions for LLM tool selection.

**Changes to existing tools**:
- **Reddit (`fetch_reddit_tool`)**: DISABLED — YARS proxy limitations make it unreliable. Remove from agent tools list. Keep code for future re-enabling.
- **Firecrawl (`fetch_web_tool`)**: Demoted to FALLBACK only — used when no other tool covers the source, or for scraping a specific known URL.

**File**: `api/services/tools.py` — add 6 new tool functions, keep youtube + amazon + clean_noise

```python
# === TECH / PROGRAMMING CATEGORY ===

async def fetch_hackernews_tool(ctx: RunContext, query: str) -> str:
    """Fetch discussions from Hacker News (Y Combinator's tech community).
    SOURCE: Hacker News (news.ycombinator.com) via Algolia search API.
    BEST FOR: tech news, startup discussions, developer opinions, programming tools,
    open source projects, AI/ML announcements, Silicon Valley trends.
    SENTIMENT VALUE: High — HN comments contain strong developer opinions and debates.
    NOT FOR: world politics, sports, entertainment, consumer product reviews."""

async def fetch_devto_tool(ctx: RunContext, query: str) -> str:
    """Fetch developer blog posts and discussions from Dev.to community.
    SOURCE: Dev.to API (dev.to/api). Returns full article markdown + comments.
    BEST FOR: developer tutorials, coding best practices, framework comparisons,
    developer experience discussions, tech career topics, project showcases.
    SENTIMENT VALUE: High — community reactions (❤️) + threaded comments with opinions.
    NOT FOR: breaking news, world politics, product reviews, non-tech topics."""

async def fetch_stackexchange_tool(ctx: RunContext, query: str) -> str:
    """Fetch Q&A from Stack Overflow / Stack Exchange.
    SOURCE: Stack Overflow API (api.stackexchange.com).
    BEST FOR: programming questions, technical troubleshooting, library/framework
    comparisons, error messages, code examples, best practices.
    SENTIMENT VALUE: Medium — vote scores indicate community consensus on answers.
    NOT FOR: product reviews, news, opinions, non-technical topics."""

# === NEWS / WORLD EVENTS CATEGORY ===

async def fetch_guardian_tool(ctx: RunContext, query: str) -> str:
    """Fetch full-text articles from The Guardian newspaper.
    SOURCE: Guardian Content API (content.guardianapis.com). Returns complete article body.
    BEST FOR: in-depth world news, politics, international relations, economics,
    environment/climate, conflicts, trade policy, investigative journalism.
    SENTIMENT VALUE: Low — factual journalism, no user comments. Use for information depth.
    NOT FOR: programming questions, product reviews, tech community discussions."""

async def fetch_news_tool(ctx: RunContext, query: str) -> str:
    """Fetch headlines and summaries from major news outlets via RSS feeds.
    SOURCE: BBC World, Reuters, AP News, NPR, Al Jazeera, NYT (via RSS/RSSHub).
    BEST FOR: breaking news, current events, broad news coverage across multiple outlets.
    Provides breadth (many sources) but less depth than Guardian (summaries only).
    SENTIMENT VALUE: Low — news summaries only, no user comments. Use for breadth.
    NOT FOR: in-depth analysis, programming questions, product reviews."""

# === CROSS-CATEGORY (universal) ===

# YouTube (existing) — add SENTIMENT VALUE annotation to docstring:
# SENTIMENT VALUE: High — video comments contain diverse user opinions. Universal tool.

# Amazon (existing) — add SENTIMENT VALUE annotation to docstring:
# SENTIMENT VALUE: High — product reviews and ratings are pure sentiment data.

# === GENERAL / FALLBACK CATEGORY ===

async def search_web_tool(ctx: RunContext, query: str) -> str:
    """Search the entire web using Tavily AI search engine.
    SOURCE: Tavily search API — searches and curates results from across the web.
    BEST FOR: topics not covered by other tools, niche subjects, discovering content
    from sources not in our tool set, fact-checking, finding specific information.
    USE AS FALLBACK: only when other specific tools don't cover what you need."""

async def fetch_web_tool(ctx: RunContext, url: str) -> str:
    """Scrape a specific web page by URL using Firecrawl.
    SOURCE: Any URL — uses Firecrawl to extract clean markdown content.
    BEST FOR: when you already know a specific URL that needs analysis.
    NOT FOR: general search or discovery — use search_web_tool instead.
    FALLBACK ONLY: use other tools first, this is for specific URL extraction."""
```

**Total active tools: 10** (youtube, amazon, clean_noise + hackernews, devto, stackexchange, guardian, news, search_web, web)
- Reddit: disabled (YARS proxy issues)
- Firecrawl: fallback only
- YouTube: cross-category (universal, always available)

### A4: System Prompt — LLM Tool Selection Strategy

**File**: `api/services/agent.py`

Updated `SYSTEM_PROMPT` with explicit tool selection guidance:

```
You are SmIA (Social Media Intelligence Agent), an expert analyst that fetches
and analyzes information from multiple sources.

## TOOL SELECTION STRATEGY

You have access to multiple data source tools. Choose 2-4 tools most relevant
to the user's query. DO NOT call all tools — select based on the topic:

### Tech / Programming / AI topics:
→ Use: fetch_hackernews, fetch_devto, fetch_stackexchange, fetch_youtube
→ Hacker News for tech news, developer opinions, startup discussions
→ Dev.to for developer tutorials, framework comparisons, coding practices
→ Stack Exchange for programming Q&A, technical troubleshooting
→ YouTube for tech reviews, tutorials, conference talks

### World News / Politics / Current Events:
→ Use: fetch_guardian, fetch_news
→ Guardian for in-depth journalism with full article text
→ News RSS for broad coverage across BBC, Reuters, AP, etc.

### Consumer Products / Shopping:
→ Use: fetch_amazon, fetch_youtube
→ Amazon for product reviews and ratings
→ YouTube for product review videos

### General / Niche / Mixed topics:
→ Use: search_web (Tavily) as discovery tool
→ Use: fetch_web (Firecrawl) only for specific known URLs

### Rules:
- Pick 2-4 tools, not all 10
- YouTube is a universal tool — usable across ALL categories for sentiment via comments
- If unsure, prefer Guardian + Hacker News (broadest coverage)
- **Prefer tools with no/high API limits** (HN, Dev.to, News RSS = unlimited; Guardian = 5000/day)
- **Deprioritize tools with tight API limits** (Tavily = ~33/day; Stack Exchange = 300/day without key)
- Use search_web (Tavily) only as fallback when other tools don't fit
- Use fetch_web (Firecrawl) only when you have a specific URL
- NEVER use all tools at once — it wastes time and tokens

## ANALYSIS INSTRUCTIONS
[... existing analysis instructions for TrendReport output ...]
```

- Remove `fetch_reddit_tool` from tools list (disabled)
- Update `source_breakdown` to include: `hackernews`, `devto`, `guardian`, `news_rss`, `stackexchange`, `tavily`
- Update `TrendReport.source_breakdown` validation to accept new source keys
- **Fix sentiment_timeline (bug)**: Add explicit `charts_data` format instructions to system prompt:
  ```
  charts_data: {
    "sentiment_timeline": [{"date": "YYYY-MM-DD", "score": 0.0-1.0}, ...]
    Generate sentiment scores grouped by date from the collected comments/posts.
    Score 0.0 = very negative, 0.5 = neutral, 1.0 = very positive.
  }
  ```
  Frontend (`ReportViewer.tsx`) already renders this — currently empty because LLM has no format instructions.

### A5: Additional API Integrations

**Dev.to API** (`api/services/crawler.py`):
- `fetch_devto(query, limit=10)`
- Articles endpoint: `GET https://dev.to/api/articles?tag={query}&per_page={limit}&top=7` (top 7 = last 7 days)
- Comments endpoint: `GET https://dev.to/api/comments?a_id={article_id}`
- Free, no API key needed
- Returns: `body_markdown` (full content), `comments_count`, `public_reactions_count`, `tag_list`, `user`
- Comments have threaded descendants
- Fetch top articles → for each, fetch comments → return combined

**Guardian API** (`api/services/crawler.py`):
- `fetch_guardian(query, limit=10, section=None)`
- Endpoint: `https://content.guardianapis.com/search`
- Params: `q`, `section`, `from-date`, `to-date`, `show-fields=headline,bodyText,byline,thumbnail`, `page-size`, `order-by=newest`
- API key from env: `GUARDIAN_API_KEY`
- Free: 5,000 calls/day, 12/sec — very generous
- Returns full article text (unlike RSS which only has summaries)

**Tavily API** (`api/services/crawler.py`):
- `fetch_tavily(query, limit=10, topic="general")`
- Uses official `tavily-python` async client (`AsyncTavilyClient`)
- Params: `topic="news"|"general"`, `time_range="day"|"week"`, `max_results`, `include_raw_content=False`
- API key from env: `TAVILY_API_KEY`
- Free: 1,000 credits/month (~33/day). Basic search = 1 credit
- Use sparingly: only when LLM selects it as fallback/discovery tool

**Currents API** (`api/services/crawler.py`):
- `fetch_currents_news(query, limit=10)`
- Endpoint: `https://api.currentsapi.services/v1/search`
- Free: 600 calls/day
- API key from env: `CURRENTS_API_KEY`
- Used as supplement inside `fetch_news_tool` when RSS yields < 5 items
- Skip gracefully if no API key configured

**New dependency**: `tavily-python` in `api/pyproject.toml`

### A6: Data Volume Strategy

- Per-item content cap: body ≤ 400 chars, comments: top 5 at 200 chars each
- Per-tool item cap: max 10-12 items
- System prompt: "pick 2-4 tools, not all 10"
- Result: ~15k-24k chars total input = 4k-6k tokens — well within GPT-4.1 context
- Fetch phase runs in parallel (HN/RSS/SE/Guardian APIs are fast, <5s each)
- Guardian returns full text — truncate `bodyText` to 400 chars per item in the tool
- **New tools do NOT use fetch cache** (intentional): HN, Dev.to, Guardian, SE are fast free APIs. Per-request fetching is fine. Cache can be added later if needed.
- Add `@observe` decorator (Langfuse) to all new crawler functions for tracing

---

## Part B: Multi-Topic Digests

### B1: Database Schema Changes

**File**: `api/migrations/` — new migration SQL

```sql
-- Add topic column to daily_digests (default 'ai' for existing data)
ALTER TABLE daily_digests ADD COLUMN topic TEXT NOT NULL DEFAULT 'ai';

-- Remove unique constraint on digest_date, add composite unique
ALTER TABLE daily_digests DROP CONSTRAINT IF EXISTS daily_digests_digest_date_key;
ALTER TABLE daily_digests ADD CONSTRAINT daily_digests_date_topic_key UNIQUE (digest_date, topic);

-- Add topic to collector cache
ALTER TABLE digest_collector_cache ADD COLUMN topic TEXT NOT NULL DEFAULT 'ai';
ALTER TABLE digest_collector_cache DROP CONSTRAINT IF EXISTS digest_collector_cache_digest_date_source_key;
ALTER TABLE digest_collector_cache ADD CONSTRAINT digest_collector_cache_date_source_topic_key UNIQUE (digest_date, source, topic);

-- Update RPC to accept topic parameter (MUST return JSONB — callers depend on {claimed, digest_id, current_status})
CREATE OR REPLACE FUNCTION claim_digest_generation(p_date DATE, p_topic TEXT DEFAULT 'ai')
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE v_id UUID; v_status TEXT;
BEGIN
    -- 1. Reclaim stale locks (crashed generators, 150s timeout)
    UPDATE daily_digests SET status = 'failed', updated_at = NOW()
    WHERE digest_date = p_date AND topic = p_topic
      AND status IN ('collecting', 'analyzing')
      AND updated_at < NOW() - INTERVAL '150 seconds';

    -- 2. Atomic claim: insert OR reclaim failed
    INSERT INTO daily_digests (digest_date, topic, status, updated_at)
    VALUES (p_date, p_topic, 'collecting', NOW())
    ON CONFLICT (digest_date, topic) DO UPDATE
      SET status = 'collecting', updated_at = NOW()
      WHERE daily_digests.status = 'failed'
    RETURNING id INTO v_id;

    -- 3. Did we win?
    IF v_id IS NOT NULL THEN
        RETURN jsonb_build_object('claimed', true, 'digest_id', v_id, 'current_status', 'collecting');
    ELSE
        SELECT d.id, d.status INTO v_id, v_status
        FROM daily_digests d WHERE d.digest_date = p_date AND d.topic = p_topic;
        RETURN jsonb_build_object('claimed', false, 'digest_id', v_id, 'current_status', v_status);
    END IF;
END;
$$;
```

### B2: Topic Configuration

**File**: `api/config/digest_topics.py` (NEW)

```python
DIGEST_TOPICS = {
    "ai": {
        "display_name": "AI Intelligence",
        "collectors": ["arxiv", "github", "rss", "bluesky"],
        "categories": ["Breakthrough", "Research", "Tooling", "Open Source",
                       "Infrastructure", "Product", "Policy", "Safety", "Other"],
        "rss_config": "rss_feeds.json",  # existing AI blogs
    },
    "geopolitics": {
        "display_name": "Geopolitics & Conflict",
        "collectors": ["guardian", "news_rss", "currents", "hackernews"],
        "categories": ["Conflict & Security", "Diplomacy", "Trade & Sanctions",
                       "Political Change", "Regional Tensions", "Other"],
        "rss_config": "news_rss_feeds.json",
        "guardian_sections": ["world", "politics"],
        "guardian_keywords": ["conflict", "diplomacy", "sanctions", "war"],
    },
    "climate": {
        "display_name": "Climate & Environment",
        "collectors": ["guardian", "climate_rss", "currents"],
        "categories": ["Policy & Regulation", "Extreme Weather", "Energy Transition",
                       "Research & Data", "Activism & Society", "Other"],
        "rss_config": "climate_rss_feeds.json",
        "guardian_sections": ["environment"],
        "guardian_keywords": ["climate", "energy", "emissions", "renewable"],
    },
    "health": {
        "display_name": "Health & Medical",
        "collectors": ["health_rss", "currents"],
        "categories": ["Breakthrough", "Disease & Outbreak", "Drug & Treatment",
                       "Public Health Policy", "Research", "Other"],
        "rss_config": "health_rss_feeds.json",
    },
}
```

### B3: New Digest Collectors

**Files**: `api/services/collectors/` — new collector files

**Parameterized RSS collector** (eliminates 3 duplicate files):
```python
# api/services/collectors/rss_collector.py — refactor existing class
class RssCollector:
    def __init__(self, name: str, config_file: str):
        self.name = name
        self._config_file = config_file
    async def collect(self) -> list[RawCollectorItem]: ...
```
- Existing AI RSS: `RssCollector("rss", "rss_feeds.json")` (no change in behavior)
- News RSS: `RssCollector("news_rss", "news_rss_feeds.json")`
- Climate RSS: `RssCollector("climate_rss", "climate_rss_feeds.json")`
- Health RSS: `RssCollector("health_rss", "health_rss_feeds.json")`

**Parameterized Guardian collector**:
```python
# api/services/collectors/guardian_collector.py
class GuardianCollector:
    def __init__(self, name: str, sections: list[str], keywords: list[str] | None = None):
        self.name = name
        self._sections = sections
        self._keywords = keywords
    async def collect(self) -> list[RawCollectorItem]: ...
```
- Geopolitics: `GuardianCollector("guardian", sections=["world", "politics"], keywords=["conflict", "diplomacy"])`
- Climate: `GuardianCollector("guardian_climate", sections=["environment"], keywords=["climate", "energy"])`

**Other new collectors** (unique logic, separate files):

| Collector | File | Source |
|-----------|------|--------|
| `hackernews` | `hackernews_collector.py` | HN Algolia API — top stories, 24h |
| `currents` | `currents_collector.py` | Currents API — by category param |

**New RSS configs**:
- `api/config/news_rss_feeds.json`: BBC, Reuters, AP, Guardian, Al Jazeera, NPR, NYT
- `api/config/climate_rss_feeds.json`: Guardian Climate, Carbon Brief, Climate.gov, BBC Science, InsideClimate News
- `api/config/health_rss_feeds.json`: WHO, NIH, BBC Health, STAT News, Medical News Today

### B4: Topic-Aware Digest Pipeline

**File**: `api/services/digest_service.py` — modify existing functions

- `claim_or_get_digest(user_id, access_token, topic="ai")` — add topic param
  - Line 38: pass `{"p_date": today, "p_topic": topic}` to RPC (currently only `p_date`)
  - Staleness recovery (lines 44-72) is fine — it uses `digest_id` from RPC result, already topic-scoped
- `run_digest(digest_id, topic="ai")` — filter collectors by topic config
- **Cache upsert**: change `on_conflict="digest_date,source"` → `on_conflict="digest_date,source,topic"` and pass `topic` column in upsert data
- **Hardcoded model**: change `"model_used": "gpt-4.1"` → `"model_used": settings.DIGEST_MODEL`
- **Telegram notification**: pass topic display_name to `_notify_telegram` → "Your {display_name} digest is ready"

**Topic threading (complete data flow)**:
```
Frontend: getTodayDigest(topic) → GET /today?topic=geo
  → Route: claim_or_get_digest(user_id, token, topic="geopolitics")
    → RPC: claim_digest_generation(p_date, p_topic="geopolitics")
    → if claimed: asyncio.create_task(run_digest(digest_id, topic="geopolitics"))
      → get_collectors_for_topic("geopolitics") → [guardian, news_rss, currents, hn]
      → _run_collectors(collectors, topic) → cache with (date, source, topic)
      → analyze_digest(items, topic="geopolitics") → topic-specific categories
      → save to DB with topic="geopolitics"
```

**Collector factory** (replaces global `COLLECTOR_REGISTRY` for topic-specific collectors):
```python
# In digest_service.py or new file api/services/collector_factory.py
from config.digest_topics import DIGEST_TOPICS

# Split into two dicts: simple (no config) vs parameterized (needs topic config)
SIMPLE_COLLECTORS = {
    "arxiv": lambda: ArxivCollector(),
    "github": lambda: GithubCollector(),
    "bluesky": lambda: BlueskyCollector(),
    "hackernews": lambda: HackernewsCollector(),
    "currents": lambda: CurrentsCollector(),
}

PARAMETERIZED_COLLECTORS = {
    "rss": lambda cfg: RssCollector("rss", cfg.get("rss_config", "rss_feeds.json")),
    "news_rss": lambda cfg: RssCollector("news_rss", "news_rss_feeds.json"),
    "climate_rss": lambda cfg: RssCollector("climate_rss", "climate_rss_feeds.json"),
    "health_rss": lambda cfg: RssCollector("health_rss", "health_rss_feeds.json"),
    "guardian": lambda cfg: GuardianCollector(
        "guardian",
        sections=cfg.get("guardian_sections", ["world"]),
        keywords=cfg.get("guardian_keywords"),
    ),
}

def get_collectors_for_topic(topic: str) -> list[Collector]:
    """Instantiate collectors for a given topic from DIGEST_TOPICS config."""
    topic_cfg = DIGEST_TOPICS[topic]
    collectors = []
    for name in topic_cfg["collectors"]:
        if name in SIMPLE_COLLECTORS:
            collectors.append(SIMPLE_COLLECTORS[name]())
        elif name in PARAMETERIZED_COLLECTORS:
            collectors.append(PARAMETERIZED_COLLECTORS[name](topic_cfg))
        else:
            logger.warning(f"Unknown collector: {name}")
    return collectors
```

- `_run_collectors(topic)` calls `get_collectors_for_topic(topic)` instead of iterating `COLLECTOR_REGISTRY`
- Existing AI collectors keep working via `COLLECTOR_REGISTRY` (backward compat) but are also accessible via factory
- B4 is backward-compatible via `topic="ai"` defaults — B6/B7 are required to actually USE multi-topic

### B5: Topic-Aware Digest Agent

**File**: `api/services/digest_agent.py` — dynamic agent per topic (方案 B)

- `analyze_digest(items, topic="ai")` — accept topic parameter
- **Remove module-level singleton** `digest_agent = Agent(...)`
- **Create agent dynamically** per topic — `Agent()` is a lightweight config object (zero network overhead):
  ```python
  def _create_digest_agent(topic: str) -> Agent:
      topic_cfg = DIGEST_TOPICS[topic]
      categories = " | ".join(topic_cfg["categories"])
      prompt = f"You are a {topic_cfg['display_name']} analyst...\nCategories: {categories}\n..."
      return Agent(
          model=f"openai:{settings.DIGEST_MODEL}",
          output_type=DailyDigestLLMOutput,
          system_prompt=prompt, retries=2, defer_model_check=True,
      )

  async def analyze_digest(items, topic="ai"):
      agent = _create_digest_agent(topic)
      result = await agent.run(f"Analyze these {len(items)} items:\n\n{items_text}")
      return result.output
  ```
- Each topic gets its own system prompt with topic-specific categories, importance criteria, and focus areas
- `DailyDigestLLMOutput.top_highlights`: relax `min_length=3` → `min_length=1` to handle light news days

### B6: API Route Updates

**File**: `api/routes/ai_daily_report.py`

- `GET /api/ai-daily-report/today?topic=ai` — add topic query param (default "ai")
  - Extract `topic` from query → pass to `claim_or_get_digest(user_id, token, topic=topic)`
  - Pass `topic` to `run_digest(digest_id, topic=topic)` in `asyncio.create_task()`
- `GET /api/ai-daily-report/list?topic=ai` — filter by topic, add `topic` to select clause
- `GET /api/ai-daily-report/topics` — return available topics list from `DIGEST_TOPICS`
- All existing endpoints get optional `topic` param, backward-compatible

**File**: `frontend/src/lib/api.ts`
- `getTodayDigest(topic?: string)` — append `?topic=${topic}` to endpoint
- `listDigests(topic?: string, ...)` — same

### B7: Telegram Commands

**File**: `api/services/telegram_service.py`

| Command | Topic |
|---------|-------|
| `/digest` or `/digest_ai` | AI Intelligence |
| `/digest_geo` | Geopolitics & Conflict |
| `/digest_climate` | Climate & Environment |
| `/digest_health` | Health & Medical |

### B8: Frontend Topic Switcher

**File**: `frontend/src/pages/AiDailyReport.tsx`

- Add dropdown/tabs at top of Digest page for topic selection
- Pass `topic` query param to API calls
- Update realtime subscription to filter by topic
- Each topic shows its own categories in KanbanBoard

### B9a: Digest Trigger Strategy

All topics use **lazy triggering** (same as current AI digest):
- First user to visit `/today?topic=X` triggers that topic's generation
- Subsequent users see the cached result
- This is acceptable for MVP — low traffic, each topic generates in <2 min
- Future optimization: add cron job to pre-generate all topics at 6am UTC

### B9: Configurable LLM Model

**File**: `api/core/config.py` + `api/services/digest_agent.py` + `api/services/agent.py`

- Add `ANALYSIS_MODEL` env var (default: `gpt-4.1`)
- Add `DIGEST_MODEL` env var (default: `gpt-4.1`)
- Enables future DeepSeek switch without code changes

---

## Critical Fixes (from fullstack review)

These must be addressed during implementation to prevent runtime failures:

### F1: Widen `TopDiscussion.source` type
- **File**: `api/models/schemas.py` line 11 — change `Literal["reddit", "youtube", "amazon"]` → `str`
- **File**: `shared/types.ts` line 6 — change `'reddit' | 'youtube' | 'amazon'` → `string`
- Without this, Pydantic rejects any analysis using new tools (hackernews, guardian, etc.)

### F2: Widen `CategoryType` for multi-topic digests
- **File**: `api/models/digest_schemas.py` lines 25-28 — change `CategoryType = Literal[...]` → `str`
- **File**: `shared/types.ts` line 78-87 — change `DigestCategory` union → `string`
- Without this, non-AI categories like "Conflict & Security" fail Pydantic validation
- Categories are enforced via system prompt per topic, not schema validation

### F3: Add `topic` field to DailyDigest types
- **File**: `api/models/digest_schemas.py` `DailyDigestDB` — add `topic: str = "ai"`
- **File**: `shared/types.ts` `DailyDigest` — add `topic: string`
- Frontend topic switcher needs this to know which digest belongs to which topic

### F4: Collector registry → runtime topic config
- **Problem**: `COLLECTOR_REGISTRY` is keyed by `name`. Can't register two `guardian` collectors with different configs
- **Solution**: Don't use registry for topic-specific collectors. Instead, `run_digest(topic)` creates collector instances at runtime from `DIGEST_TOPICS[topic].collectors` config, passing topic-specific params
- Keep `COLLECTOR_REGISTRY` for backward compat with existing AI collectors, but new collectors are instantiated per-topic

### F5: Add new API keys to Settings
- **File**: `api/core/config.py` — add `GUARDIAN_API_KEY`, `TAVILY_API_KEY`, `CURRENTS_API_KEY` as optional fields
- All must degrade gracefully when missing (skip that source, don't crash)

### F6: KanbanBoard dynamic categories
- **File**: `frontend/src/components/digest/KanbanBoard.tsx` — receive category config from props or `/topics` endpoint
- Don't hardcode `CATEGORY_ORDER` and `CATEGORY_COLORS` — derive from topic config
- Default color palette for unknown categories

### F7: Realtime subscription topic-aware
- **File**: `frontend/src/pages/AiDailyReport.tsx` — on topic switch, unsubscribe old subscription, re-fetch, subscribe to new digest

---

## Implementation Order

0. **Fix CLI**: Fix `api/cli/run_digest.py` stale imports (`run_collectors_phase`, `run_analysis_phase` no longer exist). Update to call current `run_digest()` with `--topic` arg. Do this first as a prerequisite — it's already broken.
1. **F1-F2**: Widen `TopDiscussion.source` + `CategoryType` to `str` (schemas + types.ts)
2. **A1-A2**: New crawler functions + RSS config files
3. **A3-A4**: New tool functions + agent registration + system prompt (incl. sentiment_timeline fix)
4. **A5**: Additional API integrations (Dev.to, Guardian, Tavily, Currents)
5. **F5 + B9**: Add API keys + configurable LLM model to Settings
6. **A6**: Tests for new tools
7. **B1 + F3**: DB migration (topic column) + add `topic` to DailyDigest types
8. **B2-B3 + F4**: Topic config + new collectors + RSS configs (runtime instantiation, not registry)
9. **B4-B5**: Topic-aware pipeline + agent (collector factory uses split dicts pattern, not try/except)
10. **B6**: API route updates (incl. `/topics` endpoint)
11. **F6-F7 + B8**: Frontend topic switcher + dynamic KanbanBoard + topic-aware subscription
12. **B7**: Telegram commands

---

## Files Summary

### New Files (~14)
| File | Purpose |
|------|---------|
| `api/config/news_rss_feeds.json` | General news RSS feeds |
| `api/config/climate_rss_feeds.json` | Climate/environment RSS feeds |
| `api/config/health_rss_feeds.json` | Health/medical RSS feeds |
| `api/config/digest_topics.py` | Topic definitions (collectors, categories, prompts) |
| `api/services/collectors/guardian_collector.py` | Guardian API collector (parameterized: sections, keywords) |
| `api/services/collectors/hackernews_collector.py` | HN collector |
| `api/services/collectors/currents_collector.py` | Currents API collector |
| `api/services/collector_factory.py` | Topic → collector instances factory |
| `api/migrations/XXX_add_digest_topics.sql` | DB migration |
| `api/tests/test_tools_hackernews.py` | HN tool tests |
| `api/tests/test_tools_news.py` | News tool tests |
| `api/tests/test_tools_devto.py` | Dev.to tool tests |
| `api/tests/test_tools_guardian.py` | Guardian tool tests |
| `api/tests/test_tools_stackexchange.py` | SE tool tests |

Note: `news_rss`, `climate_rss`, `health_rss` collectors are instances of the refactored `RssCollector(name, config_file)` — no separate files needed.

### Modified Files (~18)
| File | Changes |
|------|---------|
| `api/models/schemas.py` | F1: Widen `TopDiscussion.source` to `str` |
| `api/models/digest_schemas.py` | F2: Widen `CategoryType` to `str`; F3: Add `topic` to `DailyDigestDB`; relax `top_highlights` min_length |
| `shared/types.ts` | F1/F2/F3: Widen source/category types, add `topic` to `DailyDigest` |
| `api/services/crawler.py` | Add `fetch_hackernews`, `fetch_devto`, `fetch_news_rss`, `fetch_stackexchange`, `fetch_guardian`, `fetch_tavily`, `fetch_currents_news` |
| `api/services/tools.py` | Add 7 new tool functions |
| `api/pyproject.toml` | Add `tavily-python` dependency |
| `api/services/agent.py` | Register new tools, update system prompt, fix sentiment_timeline |
| `api/services/digest_service.py` | Topic-aware pipeline, cache upsert with topic, use collector factory, topic in notification |
| `api/services/digest_agent.py` | Dynamic agent creation per topic (方案 B), topic-specific system prompt |
| `api/services/collectors/__init__.py` | Import new collectors |
| `api/services/collectors/rss_collector.py` | Refactor to parameterized `RssCollector(name, config_file)` |
| `api/routes/ai_daily_report.py` | Add topic param + `/topics` endpoint, pass topic to run_digest |
| `api/services/telegram_service.py` | New digest commands + topic-aware notification message |
| `api/core/config.py` | Add API keys (F5) + model config env vars |
| `api/cli/run_digest.py` | Fix stale imports, add `--topic` CLI arg |
| `frontend/src/lib/api.ts` | Add `topic` param to `getTodayDigest()` and `listDigests()` |
| `frontend/src/pages/AiDailyReport.tsx` | Topic switcher + topic-aware subscription (F7) |
| `frontend/src/components/digest/KanbanBoard.tsx` | F6: Dynamic categories from props |

---

## Verification

1. **Unit tests**: `cd api && uv run python -m pytest -v`
2. **Manual Analyze test**: Query "Ukraine conflict" → should use news_rss + hackernews tools (not Amazon)
3. **Manual Analyze test**: Query "React vs Vue" → should use hackernews + stackexchange (not Reddit per instruction)
4. **Digest test**: Trigger each topic via API → verify collectors run and LLM categorizes correctly
5. **Telegram test**: `/digest_geo` → generates geopolitics digest
6. **Frontend test**: Topic switcher changes displayed digest
7. **DB check**: `daily_digests` table has topic column, multiple digests per day (one per topic)
