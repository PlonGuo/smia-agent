"""Tests for digest orchestration service."""

import sys
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from models.digest_schemas import DailyDigestLLMOutput, DigestItem, RawCollectorItem


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
        recent_time = datetime.now(UTC).isoformat()
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
        # No cached data — need three .eq() calls (digest_date, topic, digest_window)
        eq_chain = MagicMock()
        eq_chain.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value.select.return_value.eq.return_value = eq_chain
        # Upsert for caching
        mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        items = _make_sample_items()
        mock_collector = MagicMock()
        mock_collector.name = "test"
        mock_collector.collect = AsyncMock(return_value=items)

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.collector_factory.get_collectors_for_topic", return_value=[mock_collector]):
            from services.digest_service import _run_collectors
            all_items, health = await _run_collectors(mock_client, date.today().isoformat(), "ai")

            assert len(all_items) == 1
            assert health["test"] == "ok"
            mock_collector.collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_cached_data(self):
        """If cache exists for a collector, use it instead of running."""
        cached_items = [_make_sample_items()[0].model_dump(mode="json")]
        mock_client = MagicMock()
        # Cached data exists — three .eq() calls (digest_date, topic, digest_window)
        eq_chain = MagicMock()
        eq_chain.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"source": "test", "items": cached_items, "item_count": 1}]
        )
        mock_client.table.return_value.select.return_value.eq.return_value = eq_chain

        mock_collector = MagicMock()
        mock_collector.name = "test"
        mock_collector.collect = AsyncMock(return_value=[])

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.collector_factory.get_collectors_for_topic", return_value=[mock_collector]):
            from services.digest_service import _run_collectors
            all_items, health = await _run_collectors(mock_client, date.today().isoformat(), "ai")

            assert len(all_items) == 1
            assert "cached" in health["test"]
            # Collector should NOT have been called
            mock_collector.collect.assert_not_called()

    @pytest.mark.asyncio
    async def test_collector_failure_graceful(self):
        """Failed collector returns empty but doesn't crash."""
        mock_client = MagicMock()
        eq_chain = MagicMock()
        eq_chain.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value.select.return_value.eq.return_value = eq_chain

        failing_collector = MagicMock()
        failing_collector.name = "broken"
        failing_collector.collect = AsyncMock(side_effect=Exception("Network error"))

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.collector_factory.get_collectors_for_topic", return_value=[failing_collector]):
            from services.digest_service import _run_collectors
            all_items, health = await _run_collectors(mock_client, date.today().isoformat(), "ai")

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


class TestClaimOrGetDigestStaleness:
    """Lines 59-69: staleness recovery for stuck digests."""

    def test_stale_analyzing_digest_resets(self):
        """If digest is stuck 'analyzing' for >5 min, it should be reset and claimed=True."""
        from datetime import UTC, datetime, timedelta

        rpc_result = MagicMock()
        rpc_result.data = {
            "claimed": False,
            "digest_id": "d-stale",
            "current_status": "analyzing",
        }

        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = rpc_result

        # Return an updated_at that is 10 minutes ago (stale)
        stale_time = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"updated_at": stale_time}
        )
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("services.digest_service.get_supabase_client", return_value=mock_client):
            from services.digest_service import claim_or_get_digest
            result = claim_or_get_digest("user-1", "token-1")

        assert result["claimed"] is True
        assert result["status"] == "collecting"
        assert result["digest_id"] == "d-stale"

    def test_stale_collecting_digest_resets(self):
        """If digest is stuck 'collecting' for >5 min, it should also be reset."""
        from datetime import UTC, datetime, timedelta

        rpc_result = MagicMock()
        rpc_result.data = {
            "claimed": False,
            "digest_id": "d-collecting-stale",
            "current_status": "collecting",
        }

        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = rpc_result

        stale_time = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"updated_at": stale_time}
        )
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("services.digest_service.get_supabase_client", return_value=mock_client):
            from services.digest_service import claim_or_get_digest
            result = claim_or_get_digest("user-1", "token-1")

        assert result["claimed"] is True
        assert result["status"] == "collecting"

    def test_fresh_analyzing_digest_not_reset(self):
        """Digest stuck 'analyzing' for <5 min should NOT be reset."""
        from datetime import UTC, datetime, timedelta

        rpc_result = MagicMock()
        rpc_result.data = {
            "claimed": False,
            "digest_id": "d-fresh",
            "current_status": "analyzing",
        }

        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = rpc_result

        # Only 1 minute ago — not stale
        fresh_time = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"updated_at": fresh_time}
        )

        with patch("services.digest_service.get_supabase_client", return_value=mock_client):
            from services.digest_service import claim_or_get_digest
            result = claim_or_get_digest("user-1", "token-1")

        # Should NOT be claimed; should just return the current status
        assert result.get("claimed") is not True
        assert result["status"] == "analyzing"
        assert result["digest_id"] == "d-fresh"


class TestRunDigest:
    """Lines 101-193: run_digest pipeline tests."""

    @pytest.mark.asyncio
    async def test_run_digest_no_items_marks_failed(self):
        """If all collectors return empty, digest should be marked failed."""
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.digest_service._run_collectors", new_callable=AsyncMock, return_value=([], {})), \
             patch("services.digest_service.flush_langfuse"), \
             patch("langfuse.get_client"):
            from services.digest_service import run_digest
            await run_digest("d-fail-id", topic="ai")

        # Verify the update to "failed" was called
        update_calls = mock_client.table.return_value.update.call_args_list
        statuses = [call[0][0].get("status") for call in update_calls if "status" in call[0][0]]
        assert "failed" in statuses

    @pytest.mark.asyncio
    async def test_run_digest_missing_openai_key_raises(self):
        """If OPENAI_API_KEY is not set, run_digest should catch RuntimeError and mark failed."""
        from models.digest_schemas import RawCollectorItem

        items = [RawCollectorItem(title="T", url="https://x.com", source="s", snippet="s")]
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_settings = MagicMock()
        mock_settings.effective_openai_key = None  # Simulate missing key

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.digest_service._run_collectors", new_callable=AsyncMock, return_value=(items, {"s": "ok"})), \
             patch("services.digest_service.settings", mock_settings), \
             patch("services.digest_service.trace_metadata"), \
             patch("services.digest_service.flush_langfuse"), \
             patch("langfuse.get_client"):
            from services.digest_service import run_digest
            await run_digest("d-nokey", topic="ai")

        # Should update status to "failed" due to RuntimeError
        update_calls = mock_client.table.return_value.update.call_args_list
        statuses = [call[0][0].get("status") for call in update_calls if "status" in call[0][0]]
        assert "failed" in statuses

    @pytest.mark.asyncio
    async def test_run_digest_full_pipeline_success(self):
        """Lines 101-185: happy path — collectors return items, LLM succeeds, DB updated."""
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        items = _make_sample_items()
        llm_output = _make_mock_llm_output()

        mock_settings = MagicMock()
        mock_settings.effective_openai_key = "sk-test-key-1234"
        mock_settings.digest_model = "gpt-4o"

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.digest_service._run_collectors", new_callable=AsyncMock, return_value=(items, {"arxiv": "ok"})), \
             patch("services.digest_service.settings", mock_settings), \
             patch("services.digest_service.trace_metadata"), \
             patch("services.digest_service.flush_langfuse"), \
             patch("services.digest_service._notify_telegram", new_callable=AsyncMock), \
             patch("services.digest_service._cleanup_old_data"), \
             patch("langfuse.get_client") as mock_lf, \
             patch("services.digest_agent.analyze_digest", new_callable=AsyncMock, return_value=llm_output):
            mock_lf.return_value.get_current_trace_id.return_value = "trace-abc"

            from services.digest_service import run_digest
            await run_digest("d-success", topic="ai")

        # Verify at least one update to "completed"
        update_calls = mock_client.table.return_value.update.call_args_list
        statuses = [call[0][0].get("status") for call in update_calls if "status" in call[0][0]]
        assert "completed" in statuses

    @pytest.mark.asyncio
    async def test_run_digest_collector_exception_marks_failed(self):
        """Lines 187-197: unexpected exception in pipeline marks digest as failed."""
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("services.digest_service.get_supabase_client", return_value=mock_client), \
             patch("services.digest_service._run_collectors", new_callable=AsyncMock, side_effect=RuntimeError("boom")), \
             patch("services.digest_service.flush_langfuse"), \
             patch("langfuse.get_client"):
            from services.digest_service import run_digest
            await run_digest("d-exception", topic="ai")

        update_calls = mock_client.table.return_value.update.call_args_list
        statuses = [call[0][0].get("status") for call in update_calls if "status" in call[0][0]]
        assert "failed" in statuses


class TestNotifyTelegram:
    """Lines 280-287: _notify_telegram helper."""

    @pytest.mark.asyncio
    async def test_notify_telegram_calls_service(self):
        """Lines 280-287: _notify_telegram delegates to notify_digest_ready."""
        llm_output = _make_mock_llm_output()

        with patch("services.telegram_service.notify_digest_ready", new_callable=AsyncMock) as mock_notify:
            from services.digest_service import _notify_telegram
            await _notify_telegram(llm_output, total_items=5, topic="ai")

            mock_notify.assert_called_once()
            call_kwargs = mock_notify.call_args
            # total_items is the first positional arg
            assert call_kwargs[0][0] == 5

    @pytest.mark.asyncio
    async def test_notify_telegram_uses_topic_display_name(self):
        """_notify_telegram passes display_name for the topic."""
        llm_output = _make_mock_llm_output()

        with patch("services.telegram_service.notify_digest_ready", new_callable=AsyncMock) as mock_notify:
            from services.digest_service import _notify_telegram
            await _notify_telegram(llm_output, total_items=3, topic="ai")

            mock_notify.assert_called_once()
            # The topic_name kwarg should be a non-empty string
            kwargs = mock_notify.call_args[1]
            assert "topic_name" in kwargs
            assert len(kwargs["topic_name"]) > 0
