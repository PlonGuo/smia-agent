"""CLI to manually trigger digest generation.

Usage:
    cd api && uv run python -m cli.run_digest
    cd api && uv run python -m cli.run_digest --topic geopolitics
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

# Ensure api/ is on sys.path
_api_dir = str(Path(__file__).resolve().parent.parent)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from core.langfuse_config import init_langfuse


async def main(topic: str = "ai") -> None:
    init_langfuse()

    from services.database import get_supabase_client
    from services.digest_service import run_digest

    client = get_supabase_client()
    today = date.today().isoformat()

    print(f"[cli] Triggering digest for {today} (topic={topic})...")

    # Claim via RPC
    result = client.rpc("claim_digest_generation", {"p_date": today}).execute()
    row = result.data

    if not row["claimed"] and row["current_status"] == "completed":
        print(f"[cli] Digest already completed: {row['digest_id']}")
        return

    digest_id = row["digest_id"]
    print(f"[cli] Digest ID: {digest_id} (claimed={row['claimed']}, status={row['current_status']})")

    if row["claimed"] or row["current_status"] in ("collecting", "failed"):
        print("[cli] Running full digest pipeline...")
        await run_digest(digest_id)
    else:
        print(f"[cli] Status is '{row['current_status']}' — nothing to do.")

    # Check final status
    digest = (
        client.table("daily_digests")
        .select("status")
        .eq("id", digest_id)
        .single()
        .execute()
    )
    print(f"[cli] Final status: {digest.data['status']}")
    print("[cli] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manually trigger digest generation")
    parser.add_argument(
        "--topic",
        default="ai",
        help="Digest topic (default: ai)",
    )
    args = parser.parse_args()
    asyncio.run(main(topic=args.topic))
