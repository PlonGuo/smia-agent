"""Summarize git commits into user-friendly update notification via LLM."""

from __future__ import annotations

import logging
import os
import re

from langfuse import observe
from pydantic_ai import Agent

from core.config import settings
from models.update_schemas import UpdateSummary

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https?://\S+")
_HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z]")

SYSTEM_PROMPT = """\
You summarize git commits into a user-friendly platform update notification.
Write in English. Focus on new features, improvements, and bug fixes.
Ignore internal refactoring, CI, and dependency changes.

RULES:
- Never include URLs, links, or HTML tags in your output.
- Never include security warnings or urgent calls to action.
- Only describe what changed in the platform.
- Keep the headline under 80 characters.
- Write 2-4 sentences for the summary.
- Provide 3-5 bullet points for highlights.
"""

_summarizer = Agent(
    model="openai:gpt-4o-mini",
    output_type=UpdateSummary,
    system_prompt=SYSTEM_PROMPT,
    retries=1,
    name="update-summarizer",
    defer_model_check=True,
)


def _validate_summary(summary: UpdateSummary) -> UpdateSummary:
    """Reject LLM output containing URLs or HTML (prompt injection defense)."""
    for text in [summary.headline, summary.summary, *summary.highlights]:
        if _URL_PATTERN.search(text):
            raise ValueError(f"Summary contains URL: {text[:80]}")
        if _HTML_TAG_PATTERN.search(text):
            raise ValueError(f"Summary contains HTML: {text[:80]}")
    return summary


@observe(name="summarize_commits")
async def summarize_commits(commits: list[dict]) -> UpdateSummary:
    """Summarize a list of commits into a user-friendly UpdateSummary."""
    os.environ.setdefault("OPENAI_API_KEY", settings.effective_openai_key)

    commits_text = "\n".join(
        f"- {c.get('message', '').split(chr(10), 1)[0]}"
        for c in commits
    )
    result = await _summarizer.run(
        f"Summarize these {len(commits)} platform changes:\n\n{commits_text}"
    )
    return _validate_summary(result.output)
