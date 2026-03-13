"""SmIA MCP Server — exposes AI Digest content to AI clients via MCP protocol.

Fully public: no token required. Any AI client (Claude Desktop, Cursor, Windsurf)
can connect by adding the server URL to their MCP config.

Tools:
  - get_digest(topic)         — today's digest, triggers on-demand generation if needed
  - get_digest_history(topic) — last N days of digest summaries
  - list_topics()             — available topics
"""

import asyncio
import logging
from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

from config.digest_topics import DIGEST_TOPICS
from services.database import get_supabase_client
from services.digest_service import claim_or_get_digest, run_digest

logger = logging.getLogger(__name__)

mcp = FastMCP("SmIA — Social Media Intelligence Agent")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_digest(topic: str = "ai") -> str:
    """Get today's AI-curated digest for a topic.

    Available topics: ai, geopolitics, climate, health.
    If today's digest hasn't been generated yet, this triggers generation
    in the background and asks you to retry in ~1 minute.
    """
    print(f"[MCP] get_digest called: topic={topic}")

    if topic not in DIGEST_TOPICS:
        return f"Unknown topic '{topic}'. Available: {', '.join(DIGEST_TOPICS.keys())}"

    result = claim_or_get_digest(topic=topic)
    print(f"[MCP] get_digest result: status={result['status']}, claimed={result.get('claimed')}")

    if result["status"] == "completed":
        return _format_digest(result["digest"])

    if result["status"] == "failed":
        # Known MVP limitation: failed digests are not auto-reset by staleness recovery.
        # Future: extend claim_digest_generation() RPC to reset failed records.
        return (
            f"Today's {topic} digest encountered an error during generation. "
            "Please try again later."
        )

    if result.get("claimed"):
        # We won the DB lock — trigger background generation
        asyncio.create_task(run_digest(result["digest_id"], topic=topic))
        return (
            f"Today's {DIGEST_TOPICS[topic]['display_name']} digest is being generated. "
            "Please request again in ~1 minute."
        )

    # Another process already claimed generation (status: collecting or analyzing)
    return (
        f"Today's {DIGEST_TOPICS[topic]['display_name']} digest is currently being generated "
        f"(status: {result['status']}). Please request again in ~1 minute."
    )


@mcp.tool()
def get_digest_history(topic: str = "ai", days: int = 7) -> str:
    """Get the last N days of completed digests for a topic (executive summaries only).

    Useful for trend analysis. Maximum 30 days.
    """
    print(f"[MCP] get_digest_history called: topic={topic}, days={days}")

    if topic not in DIGEST_TOPICS:
        return f"Unknown topic '{topic}'. Available: {', '.join(DIGEST_TOPICS.keys())}"

    days = min(max(days, 1), 30)
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    client = get_supabase_client()  # service role
    try:
        response = (
            client.table("daily_digests")
            .select("digest_date, executive_summary, total_items, category_counts")
            .eq("topic", topic)
            .eq("status", "completed")
            .gte("digest_date", cutoff)
            .order("digest_date", desc=True)
            .limit(30)
            .execute()
        )
    except Exception as exc:
        logger.error("[MCP] get_digest_history DB error: %s", exc)
        print(f"[MCP] get_digest_history DB error: {exc}")
        return "Failed to retrieve digest history. Please try again later."

    rows = response.data
    if not rows:
        return (
            f"No completed digests found for '{topic}' in the last {days} days. "
            "Try requesting today's digest first."
        )

    display_name = DIGEST_TOPICS[topic]["display_name"]
    lines = [f"# {display_name} — Last {days} Days\n"]
    for row in rows:
        lines.append(f"## {row['digest_date']} ({row['total_items']} stories)")
        lines.append(row["executive_summary"])
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def list_topics() -> list[dict]:
    """List all available digest topics with their display names."""
    return [
        {"id": k, "name": v["display_name"]}
        for k, v in DIGEST_TOPICS.items()
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_digest(digest: dict) -> str:
    """Format a completed digest dict into AI-readable markdown."""
    topic_id = digest.get("topic", "ai")
    display_name = DIGEST_TOPICS.get(topic_id, {}).get("display_name", topic_id.title())
    digest_date = digest.get("digest_date", "Today")
    executive_summary = digest.get("executive_summary", "")
    items = digest.get("items", [])
    trending = digest.get("trending_keywords", [])

    lines = [
        f"# {digest_date} — {display_name}",
        "",
        executive_summary,
        "",
        "## Top Stories",
        "",
    ]

    # Top 10 items sorted by importance descending
    sorted_items = sorted(items, key=lambda x: x.get("importance", 0), reverse=True)[:10]
    for i, item in enumerate(sorted_items, 1):
        title = item.get("title", "")
        source = item.get("source", "")
        why = item.get("why_it_matters", "")
        url = item.get("url", "")
        lines.append(f"{i}. **{title}** ({source})")
        if why:
            lines.append(f"   {why}")
        if url:
            lines.append(f"   {url}")
        lines.append("")

    if trending:
        lines.append("## Trending Keywords")
        lines.append(", ".join(trending))

    return "\n".join(lines)
