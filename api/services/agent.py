"""PydanticAI agent configuration for multi-source social media analysis."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from langfuse import get_client, observe
from pydantic_ai import Agent

from core.config import settings
from core.langfuse_config import flush_langfuse, trace_metadata
from models.schemas import TrendReport
from services.cache import get_cached_analysis, set_cached_analysis
from services.tools import (
    clean_noise_tool,
    fetch_amazon_tool,
    fetch_devto_tool,
    fetch_guardian_tool,
    fetch_hackernews_tool,
    fetch_news_tool,
    fetch_stackexchange_tool,
    fetch_youtube_tool,
    search_web_tool,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent deps — carries query + time_range through tool calls
# ---------------------------------------------------------------------------

@dataclass
class AnalysisDeps:
    """Dependencies passed to every tool call via RunContext."""
    query: str
    time_range: str = "week"


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
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
→ Use: fetch_guardian, fetch_news, fetch_youtube
→ Guardian for in-depth journalism with full article text
→ News RSS for broad coverage across BBC, Reuters, AP, etc.

### Consumer Products / Shopping:
→ Use: fetch_amazon, fetch_youtube
→ Amazon for product reviews and ratings
→ YouTube for product review videos

### General / Niche / Mixed topics:
→ Use: search_web (Tavily) as discovery tool
→ YouTube is universal — usable across ALL categories

### Rules:
- Pick 2-4 tools, not all of them
- YouTube is a universal tool — usable across ALL categories for sentiment via comments
- If unsure, prefer Guardian + Hacker News (broadest coverage)
- Prefer tools with no/high API limits (HN, Dev.to, News RSS = unlimited; Guardian = 5000/day)
- Deprioritize tools with tight API limits (Tavily = ~33/day; Stack Exchange = 300/day)
- Use search_web (Tavily) only as fallback when other tools don't fit
- NEVER use all tools at once — it wastes time and tokens

## ANALYSIS INSTRUCTIONS

When given a user query:

1. Select 2-4 relevant tools based on the topic category above.
2. CRITICALLY FILTER the collected data before analysis:
   - DISCARD posts, comments, and reviews that are NOT about the queried topic.
   - DISCARD promotional content, ads, spam, bot comments, and generic filler.
   - ONLY use genuine user opinions, discussions, and reviews for your analysis.
3. Analyze the FILTERED data to determine overall sentiment, key themes,
   and notable discussions.
4. Return a structured TrendReport with:
   - topic: The main subject analyzed
   - sentiment: "Positive", "Negative", or "Neutral"
   - sentiment_score: 0.0 (most negative) to 1.0 (most positive)
   - summary: A 50-500 character analysis summary
   - key_insights: 3-5 bullet-point insights drawn ONLY from relevant data
   - top_discussions: Up to 15 notable posts/videos with title, url, source, score, snippet
   - keywords: 5-10 relevant keywords
   - source_breakdown: Count of RELEVANT items per source (e.g. {"hackernews": 5, "youtube": 3})
   - charts_data: Generate sentiment timeline and source distribution data:
     {
       "sentiment_timeline": [{"date": "YYYY-MM-DD", "score": 0.0-1.0}, ...],
       "source_distribution": [{"source": "hackernews", "count": 5}, ...]
     }
     For sentiment_timeline: group collected items by date, estimate sentiment per day.
     Score 0.0 = very negative, 0.5 = neutral, 1.0 = very positive.

IMPORTANT: Only include data that is genuinely about the queried topic.
If a post or article is unrelated, exclude it entirely from your analysis.
"""


def create_agent() -> Agent[AnalysisDeps, TrendReport]:
    """Create and return the SmIA analysis agent.

    The agent uses OpenAI GPT-4.1 and produces structured TrendReport outputs.
    The deps type is `AnalysisDeps` containing query + time_range.
    """
    return Agent(
        model=f"openai:{_get_model_name()}",
        output_type=TrendReport,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            fetch_youtube_tool,
            fetch_amazon_tool,
            fetch_hackernews_tool,
            fetch_devto_tool,
            fetch_stackexchange_tool,
            fetch_guardian_tool,
            fetch_news_tool,
            search_web_tool,
            clean_noise_tool,
        ],
        retries=2,
        name="smia-analyzer",
        defer_model_check=True,
    )


def _get_model_name() -> str:
    """Return the OpenAI model name to use."""
    return getattr(settings, "analysis_model", None) or "gpt-4.1"


# Singleton agent instance (created once, reused across requests).
agent = create_agent()


@observe(name="pydantic_ai_agent_run")
async def _run_agent(query: str, time_range: str = "week"):
    """Run the PydanticAI agent with Langfuse observation."""
    deps = AnalysisDeps(query=query, time_range=time_range)
    return await agent.run(query, deps=deps)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@observe()
async def analyze_topic(
    query: str,
    user_id: str,
    source: str = "web",
    session_id: str | None = None,
    time_range: str = "week",
    force_refresh: bool = False,
) -> tuple[TrendReport, bool]:
    """Run the full analysis pipeline for a user query.

    1. Checks analysis cache (unless force_refresh)
    2. Sets Langfuse trace metadata
    3. Runs the PydanticAI agent (which calls tools automatically)
    4. Enriches the result with metadata
    5. Stores result in analysis cache
    6. Flushes Langfuse events

    Returns (TrendReport, cached: bool).
    """
    # --- Tier 2 cache check: full analysis ---
    if not force_refresh:
        cached_report = get_cached_analysis(query, time_range)
        if cached_report is not None:
            try:
                report = TrendReport.model_validate(cached_report)
                report.user_id = user_id
                report.source = source  # type: ignore[assignment]
                logger.info("Returning cached analysis for '%s' (%s)", query, time_range)
                return report, True
            except Exception as exc:
                logger.warning("Cached analysis deserialization failed: %s", exc)

    start = time.time()

    # Set Langfuse trace context
    trace_metadata(
        user_id=user_id,
        session_id=session_id,
        source=source,
        tags=["analysis", source, f"time:{time_range}"],
    )

    # Set OpenAI API key for the model
    import os

    os.environ.setdefault("OPENAI_API_KEY", settings.effective_openai_key)

    # Run the agent (tool calls are traced individually via @observe on crawlers)
    result = await _run_agent(query, time_range=time_range)
    report: TrendReport = result.output

    # Enrich with metadata
    elapsed = int(time.time() - start)
    report.query = query
    report.source = source  # type: ignore[assignment]
    report.processing_time_seconds = elapsed
    report.user_id = user_id

    try:
        report.langfuse_trace_id = get_client().get_current_trace_id()
    except Exception:
        pass

    try:
        report.token_usage = {
            "total_tokens": result.usage().total_tokens if result.usage() else 0,
        }
    except Exception:
        pass

    # Store in analysis cache (exclude per-user metadata)
    cache_data = report.model_dump(mode="json", exclude={"id", "user_id", "created_at"})
    set_cached_analysis(query, time_range, cache_data)

    # Flush Langfuse
    flush_langfuse()

    return report, False
