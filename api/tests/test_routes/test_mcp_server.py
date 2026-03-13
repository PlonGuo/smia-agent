"""Tests for the MCP server tools."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

COMPLETED_DIGEST = {
    "id": "digest-123",
    "digest_date": "2026-03-12",
    "topic": "ai",
    "status": "completed",
    "executive_summary": "Big week in AI: new models released.",
    "items": [
        {
            "title": "GPT-5 Released",
            "url": "https://example.com/gpt5",
            "source": "arxiv",
            "category": "Breakthrough",
            "importance": 5,
            "why_it_matters": "Largest model yet with multimodal reasoning.",
            "also_on": [],
        },
        {
            "title": "LLM Benchmarks Updated",
            "url": "https://example.com/bench",
            "source": "github",
            "category": "Research",
            "importance": 3,
            "why_it_matters": "New standard for evaluating reasoning.",
            "also_on": [],
        },
    ],
    "top_highlights": ["GPT-5 launch", "New benchmarks"],
    "trending_keywords": ["LLM", "reasoning", "multimodal"],
    "category_counts": {"Breakthrough": 1, "Research": 1},
    "source_counts": {"arxiv": 1, "github": 1},
    "total_items": 2,
    "model_used": "gpt-4.1",
    "processing_time_seconds": 45,
    "source_health": {},
}


# ---------------------------------------------------------------------------
# _format_digest
# ---------------------------------------------------------------------------

class TestFormatDigest:
    def test_includes_date_and_topic(self):
        from routes.mcp_server import _format_digest
        result = _format_digest(COMPLETED_DIGEST)
        assert "2026-03-12" in result
        assert "AI Intelligence" in result

    def test_includes_executive_summary(self):
        from routes.mcp_server import _format_digest
        result = _format_digest(COMPLETED_DIGEST)
        assert "Big week in AI" in result

    def test_includes_top_stories(self):
        from routes.mcp_server import _format_digest
        result = _format_digest(COMPLETED_DIGEST)
        assert "GPT-5 Released" in result
        assert "Largest model yet" in result
        assert "https://example.com/gpt5" in result

    def test_sorts_items_by_importance(self):
        from routes.mcp_server import _format_digest
        result = _format_digest(COMPLETED_DIGEST)
        # GPT-5 (importance=5) should appear before LLM Benchmarks (importance=3)
        assert result.index("GPT-5 Released") < result.index("LLM Benchmarks Updated")

    def test_includes_trending_keywords(self):
        from routes.mcp_server import _format_digest
        result = _format_digest(COMPLETED_DIGEST)
        assert "LLM" in result
        assert "reasoning" in result

    def test_unknown_topic_falls_back_gracefully(self):
        from routes.mcp_server import _format_digest
        digest = {**COMPLETED_DIGEST, "topic": "unknown_topic"}
        result = _format_digest(digest)
        # Should not crash — falls back to title-cased topic id
        assert "2026-03-12" in result


# ---------------------------------------------------------------------------
# list_topics
# ---------------------------------------------------------------------------

class TestListTopics:
    def test_returns_all_four_topics(self):
        from routes.mcp_server import list_topics
        topics = list_topics()
        ids = [t["id"] for t in topics]
        assert "ai" in ids
        assert "geopolitics" in ids
        assert "climate" in ids
        assert "health" in ids

    def test_each_topic_has_id_and_name(self):
        from routes.mcp_server import list_topics
        for topic in list_topics():
            assert "id" in topic
            assert "name" in topic
            assert len(topic["name"]) > 0


# ---------------------------------------------------------------------------
# get_digest
# ---------------------------------------------------------------------------

class TestGetDigest:
    def test_invalid_topic_returns_error(self):
        from routes.mcp_server import get_digest
        result = get_digest("nonexistent_topic")
        assert "Unknown topic" in result
        assert "nonexistent_topic" in result

    def test_completed_digest_returns_formatted_markdown(self):
        from routes.mcp_server import get_digest
        with patch("routes.mcp_server.claim_or_get_digest", return_value={
            "status": "completed",
            "digest_id": "d-1",
            "digest": COMPLETED_DIGEST,
        }):
            result = get_digest("ai")
        assert "2026-03-12" in result
        assert "AI Intelligence" in result
        assert "GPT-5 Released" in result

    def test_claimed_triggers_background_task_and_returns_message(self):
        from routes.mcp_server import get_digest
        with patch("routes.mcp_server.claim_or_get_digest", return_value={
            "status": "collecting",
            "digest_id": "d-2",
            "claimed": True,
        }), patch("routes.mcp_server.asyncio.create_task") as mock_task:
            result = get_digest("ai")
        assert "being generated" in result
        assert "1 minute" in result
        mock_task.assert_called_once()

    def test_already_generating_returns_status_message(self):
        from routes.mcp_server import get_digest
        with patch("routes.mcp_server.claim_or_get_digest", return_value={
            "status": "analyzing",
            "digest_id": "d-3",
            "claimed": False,
        }):
            result = get_digest("ai")
        assert "being generated" in result
        assert "analyzing" in result

    def test_failed_status_returns_error_message(self):
        from routes.mcp_server import get_digest
        with patch("routes.mcp_server.claim_or_get_digest", return_value={
            "status": "failed",
            "digest_id": "d-4",
        }):
            result = get_digest("ai")
        assert "error" in result.lower() or "failed" in result.lower()

    def test_all_valid_topics_accepted(self):
        from routes.mcp_server import get_digest
        for topic in ["ai", "geopolitics", "climate", "health"]:
            with patch("routes.mcp_server.claim_or_get_digest", return_value={
                "status": "collecting",
                "digest_id": "d-x",
                "claimed": False,
            }):
                result = get_digest(topic)
            assert "Unknown topic" not in result


# ---------------------------------------------------------------------------
# get_digest_history
# ---------------------------------------------------------------------------

class TestGetDigestHistory:
    def test_returns_formatted_summaries(self):
        from routes.mcp_server import get_digest_history
        mock_rows = [
            {"digest_date": "2026-03-12", "executive_summary": "Summary A", "total_items": 10, "category_counts": {}},
            {"digest_date": "2026-03-11", "executive_summary": "Summary B", "total_items": 8, "category_counts": {}},
        ]
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .gte.return_value.order.return_value.limit.return_value.execute.return_value \
            .data = mock_rows

        with patch("routes.mcp_server.get_supabase_client", return_value=mock_client):
            result = get_digest_history("ai", days=7)

        assert "2026-03-12" in result
        assert "Summary A" in result
        assert "2026-03-11" in result
        assert "Summary B" in result

    def test_invalid_topic_returns_error(self):
        from routes.mcp_server import get_digest_history
        result = get_digest_history("badtopic", days=7)
        assert "Unknown topic" in result

    def test_empty_results_returns_helpful_message(self):
        from routes.mcp_server import get_digest_history
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .gte.return_value.order.return_value.limit.return_value.execute.return_value \
            .data = []

        with patch("routes.mcp_server.get_supabase_client", return_value=mock_client):
            result = get_digest_history("ai", days=7)

        assert "No completed digests" in result

    def test_days_clamped_to_30(self):
        """Passing days > 30 should be silently clamped."""
        from routes.mcp_server import get_digest_history
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .gte.return_value.order.return_value.limit.return_value.execute.return_value \
            .data = []

        with patch("routes.mcp_server.get_supabase_client", return_value=mock_client):
            # Should not raise
            result = get_digest_history("ai", days=999)
        assert "No completed digests" in result

    def test_db_error_returns_graceful_message(self):
        from routes.mcp_server import get_digest_history
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("DB connection failed")

        with patch("routes.mcp_server.get_supabase_client", return_value=mock_client):
            result = get_digest_history("ai", days=7)

        assert "Failed to retrieve" in result


# ---------------------------------------------------------------------------
# MCP app is mounted at /mcp
# ---------------------------------------------------------------------------

class TestMcpMounted:
    def test_mcp_sub_app_is_mounted(self):
        """Verify the MCP ASGI sub-app is mounted on the FastAPI app at /mcp."""
        from index import app
        mounted_paths = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/mcp" in mounted_paths
