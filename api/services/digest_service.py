"""Digest orchestrator: lazy trigger, single-phase pipeline, caching, cleanup.

Architecture: Single-phase pipeline (Fly.io long-running server).
- collect all sources → cache results → LLM analysis → save completed digest
- Runs as asyncio.create_task() from the /today endpoint
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from langfuse import get_client, observe

from core.config import settings
from core.langfuse_config import flush_langfuse, trace_metadata
from models.digest_schemas import RawCollectorItem

# COLLECTOR_REGISTRY no longer used directly — see collector_factory.py
from services.database import get_supabase_client

logger = logging.getLogger(__name__)

PT = ZoneInfo("America/Los_Angeles")


def get_current_digest_window() -> tuple[str, str]:
    """Return (digest_date_iso, window) based on current Pacific Time.

    Windows:
    - 10:00 AM PT → morning window (digest_date = today PT)
    - 5:00 PM PT  → afternoon window (digest_date = today PT)
    - Before 10 AM PT → yesterday's afternoon window
    """
    now_pt = datetime.now(PT)
    hour = now_pt.hour

    if hour >= 17:
        return now_pt.date().isoformat(), "afternoon"
    elif hour >= 10:
        return now_pt.date().isoformat(), "morning"
    else:
        # Before 10 AM — still yesterday's afternoon window
        yesterday = (now_pt - timedelta(days=1)).date()
        return yesterday.isoformat(), "afternoon"


def claim_or_get_digest(user_id: str | None = None, access_token: str | None = None, topic: str = "ai") -> dict:
    """Claim lock or return current status. Returns FAST — does NOT run pipeline.

    Called from GET /api/ai-daily-report/today and Telegram /digest.

    Includes staleness recovery: if a digest has been stuck in 'collecting' or
    'analyzing' for more than 5 minutes, it is reset to allow re-generation.
    """
    client = get_supabase_client()  # service role for RPC
    today, window = get_current_digest_window()
    print(f"[DIGEST] Window: {today} / {window} (topic={topic})")

    result = client.rpc("claim_digest_generation", {"p_date": today, "p_topic": topic, "p_window": window}).execute()
    row = result.data  # JSONB: {"claimed": bool, "digest_id": "...", "current_status": "..."}

    if not row["claimed"]:
        current_status = row["current_status"]

        # Staleness recovery: if stuck in collecting/analyzing for >5 min, reset
        if current_status in ("collecting", "analyzing"):
            digest_row = (
                client.table("daily_digests")
                .select("updated_at")
                .eq("id", row["digest_id"])
                .single()
                .execute()
            )
            updated_at = datetime.fromisoformat(
                digest_row.data["updated_at"].replace("Z", "+00:00")
            )
            stale_threshold = datetime.now(UTC) - timedelta(minutes=5)
            if updated_at < stale_threshold:
                logger.warning(
                    "Digest %s stuck at '%s' since %s — resetting to allow re-generation",
                    row["digest_id"], current_status, updated_at.isoformat(),
                )
                print(f"[DIGEST] Stale digest detected (status={current_status}, "
                      f"updated={updated_at.isoformat()}). Resetting.")
                client.table("daily_digests").update({
                    "status": "collecting",
                    "updated_at": datetime.now(UTC).isoformat(),
                }).eq("id", row["digest_id"]).execute()
                return {
                    "status": "collecting",
                    "digest_id": row["digest_id"],
                    "claimed": True,
                    "window": window,
                }

        if current_status == "completed":
            digest = (
                client.table("daily_digests")
                .select("*")
                .eq("id", row["digest_id"])
                .single()
                .execute()
            )
            return {
                "status": "completed",
                "digest_id": row["digest_id"],
                "digest": digest.data,
                "window": window,
            }
        return {"status": current_status, "digest_id": row["digest_id"], "window": window}

    # We won the race — return immediately, pipeline runs as background task
    return {"status": "collecting", "digest_id": row["digest_id"], "claimed": True, "window": window}


# ---------------------------------------------------------------------------
# Single-phase digest pipeline
# ---------------------------------------------------------------------------

@observe(name="run_digest")
async def run_digest(digest_id: str, topic: str = "ai", window: str = "morning") -> None:
    """Run the full digest pipeline: collect → analyze → save → notify."""
    client = get_supabase_client()  # service role
    today, _ = get_current_digest_window()  # use PT-based date

    try:
        # Phase 1: Collect using topic-specific collectors
        all_items, source_health = await _run_collectors(client, today, topic, window)

        if not all_items:
            # All collectors failed — mark as failed
            client.table("daily_digests").update({
                "status": "failed",
                "source_health": source_health,
                "updated_at": datetime.now(UTC).isoformat(),
            }).eq("id", digest_id).execute()
            logger.error("All collectors failed — no items to analyze")
            print("[DIGEST] All collectors failed — no items to analyze")
            return

        # Update status → analyzing
        client.table("daily_digests").update({
            "status": "analyzing",
            "source_health": source_health,
            "total_items": len(all_items),
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", digest_id).execute()

        # Phase 2: Analyze
        print(f"[DIGEST] Analysis starting for digest {digest_id}")
        trace_metadata(user_id="system:digest", tags=["digest", "analysis"])

        # Pre-flight: check OpenAI API key
        openai_key = settings.effective_openai_key
        if not openai_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured — cannot run LLM analysis. "
                "Set OPENAI_API_KEY or OPEN_AI_API_KEY in environment variables."
            )
        print(f"[DIGEST] OpenAI key present (len={len(openai_key)}, prefix={openai_key[:8]}...)")
        print(f"[DIGEST] {len(all_items)} items collected, calling LLM...")

        from services.digest_agent import DIGEST_PROMPT_VERSION, analyze_digest

        start = time.time()
        digest_output = await analyze_digest(all_items, topic=topic)
        processing_time = int(time.time() - start)

        print(f"[DIGEST] LLM analysis completed in {processing_time}s")

        # Get Langfuse trace ID
        langfuse_trace_id = None
        try:
            langfuse_trace_id = get_client().get_current_trace_id()
        except Exception:
            pass

        # Save completed digest
        client.table("daily_digests").update({
            "status": "completed",
            "executive_summary": digest_output.executive_summary,
            "items": [item.model_dump(mode="json") for item in digest_output.items],
            "top_highlights": digest_output.top_highlights,
            "trending_keywords": digest_output.trending_keywords,
            "category_counts": digest_output.category_counts,
            "source_counts": digest_output.source_counts,
            "topic": topic,
            "model_used": settings.digest_model,
            "processing_time_seconds": processing_time,
            "langfuse_trace_id": langfuse_trace_id,
            "prompt_version": DIGEST_PROMPT_VERSION,
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", digest_id).execute()

        # Cleanup old digests (30 days) + expired share tokens
        _cleanup_old_data(client)

        # Notify via Telegram
        try:
            await _notify_telegram(digest_output, len(all_items), topic=topic)
        except Exception as exc:
            logger.error("Telegram notification failed: %s", exc)

        flush_langfuse()
        logger.info("Digest completed: %d items analyzed in %ds",
                     len(all_items), processing_time)
        print(f"[DIGEST] Completed successfully: {len(all_items)} items in {processing_time}s")

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Digest pipeline failed: %s\n%s", exc, tb)
        print(f"[DIGEST] FAILED: {type(exc).__name__}: {exc}")
        print(f"[DIGEST] Traceback:\n{tb}")
        error_msg = f"[ERROR] {type(exc).__name__}: {exc}\n\n{tb[-500:]}"
        client.table("daily_digests").update({
            "status": "failed",
            "executive_summary": error_msg,
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", digest_id).execute()


async def _run_collectors(client, today: str, topic: str = "ai", window: str = "morning") -> tuple[list[RawCollectorItem], dict]:
    """Run topic-specific collectors in parallel, cache results per source+topic+window."""
    from services.collector_factory import get_collectors_for_topic

    all_items: list[RawCollectorItem] = []
    source_health: dict[str, str] = {}

    # Get collectors for this topic
    collectors = get_collectors_for_topic(topic)

    # Check cache first
    cached = (
        client.table("digest_collector_cache")
        .select("source, items, item_count")
        .eq("digest_date", today)
        .eq("topic", topic)
        .eq("digest_window", window)
        .execute()
    )
    cached_sources = {row["source"]: row for row in cached.data}

    # Determine which collectors need to run
    collectors_to_run = {}
    for collector in collectors:
        name = collector.name
        if name in cached_sources:
            items_data = cached_sources[name]["items"]
            items = [RawCollectorItem(**item) for item in items_data]
            all_items.extend(items)
            source_health[name] = "ok (cached)"
        else:
            collectors_to_run[name] = collector

    # Run missing collectors in parallel
    if collectors_to_run:
        tasks = {
            name: asyncio.create_task(collector.collect())
            for name, collector in collectors_to_run.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error("Collector %s failed: %s", name, result)
                source_health[name] = f"failed: {result}"
            else:
                source_health[name] = "ok"
                all_items.extend(result)
                # Cache results with topic dimension
                try:
                    client.table("digest_collector_cache").upsert({
                        "digest_date": today,
                        "source": name,
                        "topic": topic,
                        "digest_window": window,
                        "items": [item.model_dump(mode="json") for item in result],
                        "item_count": len(result),
                    }, on_conflict="digest_date,source,topic,digest_window").execute()
                except Exception as exc:
                    logger.error("Failed to cache %s results: %s", name, exc)

    return all_items, source_health


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup_old_data(client) -> None:
    """Delete digests and share tokens older than 30 days."""
    cutoff = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    try:
        client.table("daily_digests").delete().lt("created_at", cutoff).execute()
        client.table("digest_collector_cache").delete().lt("collected_at", cutoff).execute()
        client.table("digest_share_tokens").delete().lt("expires_at",
                     datetime.now(UTC).isoformat()).execute()
    except Exception as exc:
        logger.error("Cleanup failed: %s", exc)


async def _notify_telegram(digest_output, total_items: int, topic: str = "ai") -> None:
    """Send digest notification to authorized users with linked Telegram."""
    from config.digest_topics import DIGEST_TOPICS
    from services.telegram_service import notify_digest_ready

    topic_cfg = DIGEST_TOPICS.get(topic, {})
    display_name = topic_cfg.get("display_name", topic.title())
    categories = digest_output.category_counts
    summary = digest_output.executive_summary
    await notify_digest_ready(total_items, categories, summary, topic_name=display_name, topic=topic)
