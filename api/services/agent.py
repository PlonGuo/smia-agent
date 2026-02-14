"""PydanticAI agent configuration for multi-source social media analysis."""

from __future__ import annotations

import logging
import time
from typing import Any

from langfuse import get_client, observe
from pydantic_ai import Agent

from core.config import settings
from core.langfuse_config import flush_langfuse, trace_metadata
from models.schemas import TrendReport
from services.tools import (
    clean_noise_tool,
    fetch_amazon_tool,
    fetch_reddit_tool,
    fetch_youtube_tool,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are SmIA (Social Media Intelligence Agent), an expert analyst specializing
in social media trend analysis across Reddit, YouTube, and Amazon.

When given a user query (product name, topic, brand, etc.):

1. Use the available tools to fetch data from Reddit, YouTube, and Amazon.
   Call all three tools in parallel when appropriate.
2. Analyze the collected data to determine overall sentiment, key themes,
   and notable discussions.
3. Return a structured TrendReport with:
   - topic: The main subject analyzed
   - sentiment: "Positive", "Negative", or "Neutral"
   - sentiment_score: 0.0 (most negative) to 1.0 (most positive)
   - summary: A 50-500 character analysis summary
   - key_insights: 3-5 bullet-point insights
   - top_discussions: Up to 15 notable posts/videos with title, url, source, score, snippet
   - keywords: 5-10 relevant keywords
   - source_breakdown: Count of items per source {"reddit": N, "youtube": N, "amazon": N}
   - charts_data: Optional data for frontend charts

Focus on factual analysis. Ignore ads, spam, and off-topic content.
"""


def create_agent() -> Agent[str, TrendReport]:
    """Create and return the SmIA analysis agent.

    The agent uses OpenAI GPT-4o and produces structured TrendReport outputs.
    The deps type is `str` representing the user query as context.
    """
    return Agent(
        model=f"openai:{_get_model_name()}",
        output_type=TrendReport,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            fetch_reddit_tool,
            fetch_youtube_tool,
            fetch_amazon_tool,
            clean_noise_tool,
        ],
        retries=2,
        name="smia-analyzer",
        defer_model_check=True,
    )


def _get_model_name() -> str:
    """Return the OpenAI model name to use."""
    return "gpt-4o"


# Singleton agent instance (created once, reused across requests).
agent = create_agent()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@observe()
async def analyze_topic(
    query: str,
    user_id: str,
    source: str = "web",
    session_id: str | None = None,
) -> TrendReport:
    """Run the full analysis pipeline for a user query.

    1. Sets Langfuse trace metadata
    2. Runs the PydanticAI agent (which calls tools automatically)
    3. Enriches the result with metadata
    4. Flushes Langfuse events

    Returns a validated TrendReport.
    """
    start = time.time()

    # Set Langfuse trace context
    trace_metadata(
        user_id=user_id,
        session_id=session_id,
        source=source,
        tags=["analysis", source],
    )

    # Set OpenAI API key for the model
    import os

    os.environ.setdefault("OPENAI_API_KEY", settings.effective_openai_key)

    # Run the agent
    result = await agent.run(query, deps=query)
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

    # Flush Langfuse
    flush_langfuse()

    return report
