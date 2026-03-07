"""Tests for digest orchestration service."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date, datetime, timezone

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from models.digest_schemas import RawCollectorItem, DailyDigestLLMOutput, DigestItem


def _make_rpc_claimed():
    """RPC result: we claimed the lock."""
    resp = MagicMock()
    resp.data = {
        "claimed": True,
        "digest_id": "d-123",
        "current_status": "collecting",
    }
    return resp


def _make_rpc_already_completed():
    """RPC result: already completed."""
    resp = MagicMock()
    resp.data = {
        "claimed": False,
        "digest_id": "d-456",
        "current_status": "completed",
    }
    return resp


def _make_rpc_in_progress():
    """RPC result: someone else is running it."""
    resp = MagicMock()
    resp.data = {
        "claimed": False,
        "digest_id": "d-789",
        "current_status": "analyzing",
    }
    return resp


def _make_sample_items():
    return [
        RawCollectorItem(
            title="Test Paper",
            url="https://arxiv.org/abs/1",
            source="arxiv",
            snippet="A paper",
        ),
    ]


def _make_mock_llm_output():
    return DailyDigestLLMOutput(
        executive_summary="Test summary",
        items=[
            DigestItem(
                title="Test Paper",
                url="https://arxiv.org/abs/1",
                source="arxiv",
                category="Research",
                importance=4,
                why_it_matters="Important paper",
            ),
        ],
        top_highlights=["Test Paper published", "More stuff", "Other thing"],
        trending_keywords=["ai", "test"],
        category_counts={"Research": 1},
        source_counts={"arxiv": 1},
    )


class TestClaimOrGetDigest:
    def test_claim_lock_returns_collecting(self):
        rpc_result = _make_rpc_claimed()
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = rpc_result

        with patch("services.digest_service.get_supabase_client", return_value=mock_client):
            from services.digest_service import claim_or_get_digest
            result = claim_or_get_digest("user-1", "token-1")

            assert result["status"] == "collecting"
            assert result["digest_id"] == "d-123"
            assert result["claimed"] is True

    def test_already_completed_returns_digest(self):
        rpc_result = _make_rpc_already_completed()
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = rpc_result
        # Mock the .select().eq().single().execute() chain for fetching completed digest
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "d-456", "status": "completed", "executive_summary": "Done"}
        )

        with patch("services.digest_service.get_supabase_client", return_value=mock_client):
            from services.digest_service import claim_or_get_digest
            result = claim_or_get_digest("user-1", "token-1")

            assert result["status"] == "completed"
            assert result["digest_id"] == "d-456"
            assert result["digest"]["executive_summary"] == "Done"

    def test_in_progress_returns_status(self):
        rpc_result = _make_rpc_in_progress()
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = rpc_result
        # Mock the staleness check query — return a recent updated_at so it's NOT stale
        recent_time = datetime.now(timezone.utc).isoformat()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"updated_at": recent_time}
        )

        with patch("services.digest_service.get_supabase_client", return_value=mock_client):
            from services.digest_service import claim_or_get_digest
            result = claim_or_get_digest("user-1", "token-1")

            assert result["status"] == "analyzing"
            assert result["digest_id"] == "d-789"
            assert "claimed" not in result


class TestRunCollectors:
    @pytest.mark.asyncio
    async def test_caches_and_runs_missing(self):
        """Collectors that have cached data should be skipped; missing ones should run."""
        mock_client = MagicMock()
        # No cached data
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        # Upsert for caching
        mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        items = _make_sample_items()
        mock_collector = MagicMock()
        mock_collector.collect = AsyncMock(return_value=items)

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.digest_service.COLLECTOR_REGISTRY", {"test": mock_collector}):
            from services.digest_service import _run_collectors
            all_items, health = await _run_collectors(mock_client, date.today().isoformat())

            assert len(all_items) == 1
            assert health["test"] == "ok"
            mock_collector.collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_cached_data(self):
        """If cache exists for a collector, use it instead of running."""
        cached_items = [_make_sample_items()[0].model_dump(mode="json")]
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"source": "test", "items": cached_items, "item_count": 1}]
        )

        mock_collector = MagicMock()
        mock_collector.collect = AsyncMock(return_value=[])

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.digest_service.COLLECTOR_REGISTRY", {"test": mock_collector}):
            from services.digest_service import _run_collectors
            all_items, health = await _run_collectors(mock_client, date.today().isoformat())

            assert len(all_items) == 1
            assert "cached" in health["test"]
            # Collector should NOT have been called
            mock_collector.collect.assert_not_called()

    @pytest.mark.asyncio
    async def test_collector_failure_graceful(self):
        """Failed collector returns empty but doesn't crash."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        failing_collector = MagicMock()
        failing_collector.collect = AsyncMock(side_effect=Exception("Network error"))

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.digest_service.COLLECTOR_REGISTRY", {"broken": failing_collector}):
            from services.digest_service import _run_collectors
            all_items, health = await _run_collectors(mock_client, date.today().isoformat())

            assert all_items == []
            assert "failed" in health["broken"]


class TestCleanupOldData:
    def test_cleanup_runs_without_error(self):
        mock_client = MagicMock()
        # All delete chains
        mock_client.table.return_value.delete.return_value.lt.return_value.execute.return_value = MagicMock()

        from services.digest_service import _cleanup_old_data
        _cleanup_old_data(mock_client)

        # Verify at least 3 table calls (digests, cache, share tokens)
        assert mock_client.table.call_count >= 3

    def test_cleanup_handles_errors(self):
        mock_client = MagicMock()
        mock_client.table.return_value.delete.return_value.lt.return_value.execute.side_effect = Exception("DB error")

        from services.digest_service import _cleanup_old_data
        # Should not raise
        _cleanup_old_data(mock_client)
