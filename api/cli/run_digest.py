"""CLI to manually trigger digest generation.

Usage:
    cd api && uv run python -m cli.run_digest
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

# Ensure api/ is on sys.path
_api_dir = str(Path(__file__).resolve().parent.parent)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from core.langfuse_config import init_langfuse


async def main() -> None:
    init_langfuse()

    from services.database import get_supabase_client
    from services.digest_service import run_collectors_phase, run_analysis_phase

    client = get_supabase_client()
    today = date.today().isoformat()

    print(f"[cli] Triggering digest for {today}...")

    # Claim via RPC
    result = client.rpc("claim_digest_generation", {"p_date": today}).execute()
    row = result.data

    if not row["claimed"] and row["current_status"] == "completed":
        print(f"[cli] Digest already completed: {row['digest_id']}")
        return

    digest_id = row["digest_id"]
    print(f"[cli] Digest ID: {digest_id} (claimed={row['claimed']}, status={row['current_status']})")

    if row["claimed"] or row["current_status"] == "collecting":
        print("[cli] Running collectors phase...")
        await run_collectors_phase(digest_id)

    # Check status after collectors
    digest = (
        client.table("daily_digests")
        .select("status")
        .eq("id", digest_id)
        .single()
        .execute()
    )
    current_status = digest.data["status"]

    if current_status == "analyzing":
        print("[cli] Running analysis phase...")
        await run_analysis_phase(digest_id)
    elif current_status == "completed":
        print("[cli] Digest already completed.")
    elif current_status == "failed":
        print("[cli] Digest generation failed. Check logs.")
    else:
        print(f"[cli] Unexpected status: {current_status}")

    print("[cli] Done.")


if __name__ == "__main__":
    asyncio.run(main())
