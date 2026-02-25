"""Digest orchestrator: lazy trigger, two-phase pipeline, caching, cleanup.

Architecture: Two-phase pipeline for Vercel Hobby 60s compatibility.
- Phase 1 (collectors): Run 4 collectors → save to cache → HTTP trigger Phase 2
- Phase 2 (LLM analysis): Read cached data → analyze → save completed digest
Each phase gets its own serverless function invocation with a fresh 60s budget.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from datetime import date, datetime, timedelta, timezone

import httpx
from langfuse import get_client, observe

from core.config import settings
from core.langfuse_config import flush_langfuse, trace_metadata
from models.digest_schemas import RawCollectorItem
from services.collectors.base import COLLECTOR_REGISTRY
from services.database import get_supabase_client

logger = logging.getLogger(__name__)


def claim_or_get_digest(user_id: str, access_token: str) -> dict:
    """Claim lock or return current status. Returns FAST — does NOT run pipeline.

    Called from GET /api/ai-daily-report/today.
    """
    client = get_supabase_client()  # service role for RPC
    today = date.today().isoformat()

    result = client.rpc("claim_digest_generation", {"p_date": today}).execute()
    row = result.data  # JSONB: {"claimed": bool, "digest_id": "...", "current_status": "..."}

    if not row["claimed"]:
        if row["current_status"] == "completed":
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
            }
        return {"status": row["current_status"], "digest_id": row["digest_id"]}

    # We won the race — return immediately, pipeline runs in BackgroundTask
    return {"status": "collecting", "digest_id": row["digest_id"], "claimed": True}


# ---------------------------------------------------------------------------
# Phase 1: Collectors (runs in BackgroundTask of /today endpoint)
# ---------------------------------------------------------------------------

@observe(name="run_collectors_phase")
async def run_collectors_phase(digest_id: str) -> None:
    """Phase 1: Run all collectors, cache results, trigger Phase 2.

    Runs as BackgroundTask in the /today endpoint's serverless function.
    """
    client = get_supabase_client()  # service role
    today = date.today().isoformat()

    try:
        # Import collectors to trigger registration
        import services.collectors  # noqa: F401

        # Run all collectors in parallel
        all_items, source_health = await _run_collectors(client, today)

        if not all_items:
            # All collectors failed — mark as failed
            client.table("daily_digests").update({
                "status": "failed",
                "source_health": source_health,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", digest_id).execute()
            logger.error("All collectors failed — no items to analyze")
            return

        # Update status → analyzing
        client.table("daily_digests").update({
            "status": "analyzing",
            "source_health": source_health,
            "total_items": len(all_items),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", digest_id).execute()

        # Trigger Phase 2 via internal HTTP call
        await _trigger_analysis_phase(digest_id)

    except Exception as exc:
        logger.error("Collectors phase failed: %s", exc)
        client.table("daily_digests").update({
            "status": "failed",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", digest_id).execute()


async def _run_collectors(client, today: str) -> tuple[list[RawCollectorItem], dict]:
    """Run all collectors in parallel, cache results per source."""
    all_items: list[RawCollectorItem] = []
    source_health: dict[str, str] = {}

    # Check cache first
    cached = (
        client.table("digest_collector_cache")
        .select("source, items, item_count")
        .eq("digest_date", today)
        .execute()
    )
    cached_sources = {row["source"]: row for row in cached.data}

    # Determine which collectors need to run
    collectors_to_run = {}
    for name, collector in COLLECTOR_REGISTRY.items():
        if name in cached_sources:
            # Use cached data
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
                # Cache results
                try:
                    client.table("digest_collector_cache").upsert({
                        "digest_date": today,
                        "source": name,
                        "items": [item.model_dump(mode="json") for item in result],
                        "item_count": len(result),
                    }, on_conflict="digest_date,source").execute()
                except Exception as exc:
                    logger.error("Failed to cache %s results: %s", name, exc)

    return all_items, source_health


async def _trigger_analysis_phase(digest_id: str) -> None:
    """Trigger Phase 2 via internal HTTP call to a new serverless function."""
    app_url = settings.effective_app_url

    if not app_url:
        # No app_url configured — fall back to running Phase 2 inline
        logger.warning("No APP_URL or VERCEL_URL configured — running Phase 2 inline")
        print("[DIGEST] No APP_URL or VERCEL_URL — running Phase 2 inline")
        await run_analysis_phase(digest_id)
        return

    try:
        print(f"[DIGEST] Triggering Phase 2 via {app_url}/api/ai-daily-report/internal/analyze")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{app_url}/api/ai-daily-report/internal/analyze",
                json={"digest_id": digest_id},
                headers={"x-internal-secret": settings.internal_secret},
            )
            if resp.status_code != 200:
                logger.error("Phase 2 trigger failed: %s %s", resp.status_code, resp.text)
                print(f"[DIGEST] Phase 2 HTTP trigger failed ({resp.status_code}), running inline")
                await run_analysis_phase(digest_id)
            else:
                print(f"[DIGEST] Phase 2 triggered successfully via HTTP")
    except Exception as exc:
        logger.error("Phase 2 trigger HTTP failed: %s — running inline", exc)
        print(f"[DIGEST] Phase 2 HTTP error: {exc} — running inline")
        await run_analysis_phase(digest_id)


# ---------------------------------------------------------------------------
# Phase 2: LLM Analysis (runs in BackgroundTask of /internal/analyze endpoint)
# ---------------------------------------------------------------------------

@observe(name="run_analysis_phase")
async def run_analysis_phase(digest_id: str) -> None:
    """Phase 2: Read cached collector data, run LLM, save completed digest."""
    client = get_supabase_client()  # service role
    today = date.today().isoformat()

    try:
        print(f"[DIGEST] Phase 2 starting for digest {digest_id}")
        trace_metadata(tags=["digest", "analysis"])

        # Pre-flight: check OpenAI API key
        openai_key = settings.effective_openai_key
        if not openai_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured — cannot run LLM analysis. "
                "Set OPENAI_API_KEY or OPEN_AI_API_KEY in Vercel env vars."
            )
        print(f"[DIGEST] OpenAI key present (len={len(openai_key)}, prefix={openai_key[:8]}...)")

        # Read collector cache
        cached = (
            client.table("digest_collector_cache")
            .select("source, items")
            .eq("digest_date", today)
            .execute()
        )
        all_items = []
        for row in cached.data:
            for item_data in row["items"]:
                all_items.append(RawCollectorItem(**item_data))

        if not all_items:
            client.table("daily_digests").update({
                "status": "failed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", digest_id).execute()
            logger.error("No cached items found for analysis")
            print("[DIGEST] Phase 2 failed: no cached items found")
            return

        print(f"[DIGEST] Phase 2: {len(all_items)} items loaded from cache, calling LLM...")

        # Run LLM analysis
        from services.digest_agent import analyze_digest, DIGEST_PROMPT_VERSION

        start = time.time()
        digest_output = await analyze_digest(all_items)
        processing_time = int(time.time() - start)

        print(f"[DIGEST] LLM analysis completed in {processing_time}s")

        # Get token usage and trace ID
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
            "model_used": "gpt-4.1",
            "processing_time_seconds": processing_time,
            "langfuse_trace_id": langfuse_trace_id,
            "prompt_version": DIGEST_PROMPT_VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", digest_id).execute()

        # Cleanup old digests (30 days) + expired share tokens
        _cleanup_old_data(client)

        # Notify via Telegram
        try:
            await _notify_telegram(digest_output, len(all_items))
        except Exception as exc:
            logger.error("Telegram notification failed: %s", exc)

        flush_langfuse()
        logger.info("Digest completed: %d items analyzed in %ds",
                     len(all_items), processing_time)
        print(f"[DIGEST] Phase 2 completed successfully: {len(all_items)} items in {processing_time}s")

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Analysis phase failed: %s\n%s", exc, tb)
        print(f"[DIGEST] Phase 2 FAILED: {type(exc).__name__}: {exc}")
        print(f"[DIGEST] Traceback:\n{tb}")
        client.table("daily_digests").update({
            "status": "failed",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", digest_id).execute()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup_old_data(client) -> None:
    """Delete digests and share tokens older than 30 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    try:
        client.table("daily_digests").delete().lt("created_at", cutoff).execute()
        client.table("digest_collector_cache").delete().lt("collected_at", cutoff).execute()
        client.table("digest_share_tokens").delete().lt("expires_at",
                     datetime.now(timezone.utc).isoformat()).execute()
    except Exception as exc:
        logger.error("Cleanup failed: %s", exc)


async def _notify_telegram(digest_output, total_items: int) -> None:
    """Send digest notification to authorized users with linked Telegram."""
    from services.telegram_service import notify_digest_ready

    categories = digest_output.category_counts
    await notify_digest_ready(total_items, categories)
