"""PydanticAI agent for categorizing, scoring, and summarizing collected items."""

from __future__ import annotations

import logging
import os

from langfuse import observe
from pydantic_ai import Agent

from config.digest_topics import DIGEST_TOPICS
from core.config import settings
from models.digest_schemas import DailyDigestLLMOutput, RawCollectorItem

logger = logging.getLogger(__name__)

DIGEST_PROMPT_VERSION = "v1.1"


def _build_system_prompt(topic: str) -> str:
    """Build a topic-specific system prompt for the digest agent."""
    topic_cfg = DIGEST_TOPICS[topic]
    display_name = topic_cfg["display_name"]
    categories = " | ".join(topic_cfg["categories"])
    collectors = ", ".join(topic_cfg["collectors"])

    return f"""\
You are a {display_name} analyst producing a daily intelligence digest. Given a list
of items collected from {collectors}:

1. **Categorize** each item into exactly one category:
   {categories}

2. **Score importance** (1-5) based on potential impact on practitioners and readers:
   5 = Major breakthrough or paradigm shift
   4 = Significant advancement or widely-covered story
   3 = Notable development or useful update
   2 = Incremental progress or niche topic
   1 = Minor update or tangential content

3. **Deduplicate**: If the same news appears from multiple sources, merge into
   one item. Set the primary source and list others in "also_on".

4. **Extract trending keywords** across all items (5-15 tags).

5. **Write executive summary** highlighting cross-source themes (2-3 sentences).
   Focus on what readers interested in {display_name} should know today.

6. **Select top 3-5 highlights** — the most impactful items of the day.

7. **Write "why_it_matters"** for each item (10-200 chars). Be specific and
   practitioner-focused, not generic.

Be concise, precise, and focus on what matters for {display_name}.
Discard irrelevant or low-quality items. Quality over quantity.
"""


def _create_digest_agent(topic: str) -> Agent[None, DailyDigestLLMOutput]:
    """Create a digest agent configured for a specific topic.

    Agent() is a lightweight config object — no network overhead.
    """
    return Agent(
        model=f"openai:{settings.digest_model}",
        output_type=DailyDigestLLMOutput,
        system_prompt=_build_system_prompt(topic),
        retries=2,
        name=f"digest-{topic}",
        defer_model_check=True,
    )


@observe(name="analyze_digest")
async def analyze_digest(
    items: list[RawCollectorItem],
    topic: str = "ai",
) -> DailyDigestLLMOutput:
    """Run the digest agent on collected items. Returns structured LLM output."""
    os.environ.setdefault("OPENAI_API_KEY", settings.effective_openai_key)

    topic_cfg = DIGEST_TOPICS.get(topic, DIGEST_TOPICS["ai"])
    display_name = topic_cfg["display_name"]

    items_text = "\n".join(
        f"[{i.source}] {i.title} — {i.snippet or 'no description'} ({i.url})"
        for i in items
    )

    agent = _create_digest_agent(topic)
    result = await agent.run(
        f"Analyze these {len(items)} items from today's {display_name} ecosystem:\n\n{items_text}"
    )
    return result.output
