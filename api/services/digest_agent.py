"""PydanticAI agent for categorizing, scoring, and summarizing collected items."""

from __future__ import annotations

import logging
import os

from langfuse import observe
from pydantic_ai import Agent

from core.config import settings
from models.digest_schemas import DailyDigestLLMOutput, RawCollectorItem

logger = logging.getLogger(__name__)

DIGEST_PROMPT_VERSION = "v1.0"

SYSTEM_PROMPT = """\
You are an AI research analyst producing a daily intelligence digest. Given a list
of items collected from arXiv, GitHub, RSS feeds, and Bluesky:

1. **Categorize** each item into exactly one category:
   Breakthrough | Research | Tooling | Open Source | Infrastructure | Product | Policy | Safety | Other

2. **Score importance** (1-5) based on potential impact on AI practitioners:
   5 = Major breakthrough or paradigm shift
   4 = Significant advancement or widely-used tool release
   3 = Notable research or useful tool update
   2 = Incremental progress or niche topic
   1 = Minor update or tangential content

3. **Deduplicate**: If the same news appears from multiple sources, merge into
   one item. Set the primary source and list others in "also_on".

4. **Extract trending keywords** across all items (5-15 tags).

5. **Write executive summary** highlighting cross-source themes (2-3 sentences).
   Focus on what practitioners should know today.

6. **Select top 3-5 highlights** — the most impactful items of the day.

7. **Write "why_it_matters"** for each item (10-200 chars). Be specific and
   practitioner-focused, not generic.

Be concise, precise, and focus on what AI/ML practitioners care about.
Discard irrelevant or low-quality items. Quality over quantity.
"""

digest_agent = Agent(
    model="openai:gpt-4.1",
    output_type=DailyDigestLLMOutput,
    system_prompt=SYSTEM_PROMPT,
    retries=2,
    name="digest-analyzer",
    defer_model_check=True,
)


@observe(name="analyze_digest")
async def analyze_digest(items: list[RawCollectorItem]) -> DailyDigestLLMOutput:
    """Run the digest agent on collected items. Returns structured LLM output (I9)."""
    os.environ.setdefault("OPENAI_API_KEY", settings.effective_openai_key)

    items_text = "\n".join(
        f"[{i.source}] {i.title} — {i.snippet or 'no description'} ({i.url})"
        for i in items
    )
    result = await digest_agent.run(
        f"Analyze these {len(items)} items from today's AI ecosystem:\n\n{items_text}"
    )
    return result.output  # PydanticAI v1.59 uses .output (I2)
