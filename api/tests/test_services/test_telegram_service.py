"""Tests for the Telegram bot service (message formatting + command handlers)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.telegram_service import (
    _escape_html,
    _parse_topic_and_time_range,
    format_analysis_result,
    format_error,
    format_help,
    format_history,
    format_welcome,
    handle_analyze,
    handle_bind,
    handle_digest,
    handle_help,
    handle_history,
    handle_start,
    handle_update,
    notify_digest_ready,
    send_message,
    send_typing_action,
)
from tests.conftest import make_trend_report_data

# ---------------------------------------------------------------------------
# Message formatting tests
# ---------------------------------------------------------------------------


class TestEscapeHtml:
    def test_escapes_ampersand(self):
        assert _escape_html("A & B") == "A &amp; B"

    def test_escapes_angle_brackets(self):
        assert _escape_html("<b>") == "&lt;b&gt;"

    def test_no_change_for_plain_text(self):
        assert _escape_html("hello world") == "hello world"


class TestFormatAnalysisResult:
    def test_contains_topic(self):
        data = make_trend_report_data()
        result = format_analysis_result(data)
        assert "Test Topic" in result

    def test_contains_sentiment(self):
        data = make_trend_report_data(sentiment="Positive", sentiment_score=0.85)
        result = format_analysis_result(data)
        assert "Positive" in result
        assert "0.85" in result

    def test_contains_key_insights(self):
        data = make_trend_report_data()
        result = format_analysis_result(data)
        assert "insight1" in result

    def test_contains_source_breakdown(self):
        data = make_trend_report_data(source_breakdown={"reddit": 30, "youtube": 20})
        result = format_analysis_result(data)
        assert "Reddit: 30" in result
        assert "Youtube: 20" in result

    def test_contains_report_link(self):
        data = make_trend_report_data()
        result = format_analysis_result(data, report_id="abc-123")
        assert "reports/abc-123" in result

    def test_no_link_without_report_id(self):
        data = make_trend_report_data()
        result = format_analysis_result(data, report_id=None)
        assert "reports/" not in result

    def test_positive_emoji(self):
        data = make_trend_report_data(sentiment="Positive")
        result = format_analysis_result(data)
        assert "\U0001f60a" in result

    def test_negative_emoji(self):
        data = make_trend_report_data(sentiment="Negative")
        result = format_analysis_result(data)
        assert "\U0001f61f" in result

    def test_neutral_emoji(self):
        data = make_trend_report_data(sentiment="Neutral")
        result = format_analysis_result(data)
        assert "\U0001f610" in result

    def test_html_escaping_in_topic(self):
        data = make_trend_report_data(topic="<script>alert('xss')</script>")
        result = format_analysis_result(data)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_processing_time_shown(self):
        """Line 128: processing_time present → timing line rendered."""
        data = make_trend_report_data()
        data["processing_time_seconds"] = 12
        result = format_analysis_result(data)
        assert "12s" in result


class TestFormatHistory:
    def test_empty_history(self):
        result = format_history([])
        assert "No analysis history" in result

    def test_with_reports(self):
        reports = [
            {
                "id": "r1",
                "topic": "Topic 1",
                "sentiment": "Positive",
                "created_at": "2026-02-14T10:30:00+00:00",
            },
            {
                "id": "r2",
                "topic": "Topic 2",
                "sentiment": "Negative",
                "created_at": "2026-02-14T09:00:00+00:00",
            },
        ]
        result = format_history(reports)
        assert "Topic 1" in result
        assert "Topic 2" in result
        assert "Positive" in result
        assert "reports/r1" in result

    def test_limits_to_5(self):
        reports = [
            {"id": f"r{i}", "topic": f"Topic {i}", "sentiment": "Neutral"}
            for i in range(10)
        ]
        result = format_history(reports)
        assert "Topic 4" in result
        assert "Topic 5" not in result  # 0-indexed, so 5th item is Topic 4

    def test_invalid_created_at_falls_back(self):
        """Line 151-152: invalid datetime string falls back to first 10 chars."""
        reports = [
            {
                "id": "r1",
                "topic": "Topic 1",
                "sentiment": "Positive",
                "created_at": "not-a-valid-date",
            }
        ]
        result = format_history(reports)
        assert "Topic 1" in result
        # The fallback uses first 10 chars of the bad string
        assert "not-a-vali" in result

    def test_report_without_id_no_link(self):
        """Line 156: report_id empty → no link appended."""
        reports = [
            {
                "id": "",
                "topic": "No Link Topic",
                "sentiment": "Neutral",
                "created_at": "",
            }
        ]
        result = format_history(reports)
        assert "No Link Topic" in result
        assert "View report" not in result


class TestFormatWelcome:
    def test_contains_bot_name(self):
        result = format_welcome()
        assert "SmIA Bot" in result

    def test_contains_commands(self):
        result = format_welcome()
        assert "/analyze" in result
        assert "/history" in result
        assert "/bind" in result
        assert "/help" in result


class TestFormatHelp:
    def test_contains_all_commands(self):
        result = format_help()
        assert "/analyze" in result
        assert "/history" in result
        assert "/bind" in result
        assert "/help" in result

    def test_contains_web_link(self):
        result = format_help()
        # URL comes from settings.effective_app_url or fallback
        assert "smia-agent" in result


class TestFormatError:
    def test_has_warning_emoji(self):
        result = format_error("something broke")
        assert "\u26a0\ufe0f" in result
        assert "something broke" in result


# ---------------------------------------------------------------------------
# Command handler tests
# ---------------------------------------------------------------------------


class TestHandleStart:
    @pytest.mark.asyncio
    async def test_sends_welcome(self):
        with patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send:
            await handle_start(chat_id=123)
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "SmIA Bot" in msg


class TestHandleHelp:
    @pytest.mark.asyncio
    async def test_sends_help(self):
        with patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send:
            await handle_help(chat_id=123)
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "/analyze" in msg


class TestHandleAnalyze:
    @pytest.mark.asyncio
    async def test_unbound_user_gets_error(self):
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=None),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_analyze(chat_id=123, telegram_user_id=456, topic="test topic")
        msg = mock_send.call_args[0][1]
        assert "bind" in msg.lower()

    @pytest.mark.asyncio
    async def test_short_topic_gets_error(self):
        binding = {"user_id": "uid-1"}
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_analyze(chat_id=123, telegram_user_id=456, topic="ab")
        msg = mock_send.call_args[0][1]
        assert "provide a topic" in msg.lower()

    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        binding = {"user_id": "uid-1"}
        mock_report = MagicMock()
        mock_report.model_dump.return_value = make_trend_report_data()

        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
            patch("services.telegram_service.send_typing_action", new_callable=AsyncMock),
            patch("services.agent.analyze_topic", new_callable=AsyncMock, return_value=(mock_report, False)),
            patch("services.telegram_service.save_report_service", return_value={"id": "r-123"}),
        ):
            await handle_analyze(chat_id=123, telegram_user_id=456, topic="Plaud Note")

        # Should have sent analyzing msg + result msg
        assert mock_send.call_count == 2
        result_msg = mock_send.call_args_list[1][0][1]
        assert "Analysis Complete" in result_msg

    @pytest.mark.asyncio
    async def test_analysis_failure_sends_error(self):
        binding = {"user_id": "uid-1"}

        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
            patch("services.telegram_service.send_typing_action", new_callable=AsyncMock),
            patch("services.agent.analyze_topic", new_callable=AsyncMock, side_effect=RuntimeError("fail")),
        ):
            await handle_analyze(chat_id=123, telegram_user_id=456, topic="test topic")

        last_msg = mock_send.call_args_list[-1][0][1]
        assert "failed" in last_msg.lower()


class TestHandleBind:
    @pytest.mark.asyncio
    async def test_invalid_code_length(self):
        with patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send:
            await handle_bind(chat_id=123, telegram_user_id=456, code="AB")
        msg = mock_send.call_args[0][1]
        assert "6 characters" in msg

    @pytest.mark.asyncio
    async def test_already_bound(self):
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value={"user_id": "uid"}),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_bind(chat_id=123, telegram_user_id=456, code="ABC123")
        msg = mock_send.call_args[0][1]
        assert "already linked" in msg.lower()

    @pytest.mark.asyncio
    async def test_invalid_code(self):
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=None),
            patch("services.telegram_service.lookup_bind_code", return_value=None),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_bind(chat_id=123, telegram_user_id=456, code="BADCDE")
        msg = mock_send.call_args[0][1]
        assert "invalid" in msg.lower() or "expired" in msg.lower()

    @pytest.mark.asyncio
    async def test_successful_bind(self):
        mock_binding_data = {"user_id": "uid", "bind_code": "ABC123"}
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=None),
            patch("services.telegram_service.lookup_bind_code", return_value=mock_binding_data),
            patch("services.telegram_service.complete_binding", return_value={"user_id": "uid"}),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_bind(chat_id=123, telegram_user_id=456, code="ABC123")
        msg = mock_send.call_args[0][1]
        assert "linked successfully" in msg.lower()

    @pytest.mark.asyncio
    async def test_code_uppercased(self):
        """bind code is uppercased before lookup."""
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=None),
            patch("services.telegram_service.lookup_bind_code", return_value=None) as mock_lookup,
            patch("services.telegram_service.send_message", new_callable=AsyncMock),
        ):
            await handle_bind(chat_id=123, telegram_user_id=456, code="abc123")
        mock_lookup.assert_called_once_with("ABC123")


class TestHandleHistory:
    @pytest.mark.asyncio
    async def test_unbound_user_gets_error(self):
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=None),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_history(chat_id=123, telegram_user_id=456)
        msg = mock_send.call_args[0][1]
        assert "bind" in msg.lower()

    @pytest.mark.asyncio
    async def test_bound_user_gets_history(self):
        binding = {"user_id": "uid-1"}
        reports = [
            {"id": "r1", "topic": "Topic 1", "sentiment": "Positive"},
        ]
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.get_recent_reports_by_user", return_value=reports),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_history(chat_id=123, telegram_user_id=456)
        msg = mock_send.call_args[0][1]
        assert "Topic 1" in msg


# ---------------------------------------------------------------------------
# Update dispatcher tests
# ---------------------------------------------------------------------------


class TestHandleUpdate:
    @pytest.mark.asyncio
    async def test_start_command(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 123},
                "chat": {"id": 123, "type": "private"},
                "text": "/start",
            },
        }
        with patch("services.telegram_service.handle_start", new_callable=AsyncMock) as mock:
            await handle_update(update)
        mock.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_help_command(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 123},
                "chat": {"id": 123, "type": "private"},
                "text": "/help",
            },
        }
        with patch("services.telegram_service.handle_help", new_callable=AsyncMock) as mock:
            await handle_update(update)
        mock.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_analyze_command(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 456},
                "chat": {"id": 456, "type": "private"},
                "text": "/analyze Plaud Note reviews",
            },
        }
        with patch("services.telegram_service.handle_analyze", new_callable=AsyncMock) as mock:
            await handle_update(update)
        mock.assert_called_once_with(456, 456, "Plaud Note reviews")

    @pytest.mark.asyncio
    async def test_bind_command(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 789},
                "chat": {"id": 789, "type": "private"},
                "text": "/bind ABC123",
            },
        }
        with patch("services.telegram_service.handle_bind", new_callable=AsyncMock) as mock:
            await handle_update(update)
        mock.assert_called_once_with(789, 789, "ABC123")

    @pytest.mark.asyncio
    async def test_history_command(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 321},
                "chat": {"id": 321, "type": "private"},
                "text": "/history",
            },
        }
        with patch("services.telegram_service.handle_history", new_callable=AsyncMock) as mock:
            await handle_update(update)
        mock.assert_called_once_with(321, 321)

    @pytest.mark.asyncio
    async def test_unknown_command(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 123},
                "chat": {"id": 123, "type": "private"},
                "text": "/foobar",
            },
        }
        with patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send:
            await handle_update(update)
        msg = mock_send.call_args[0][1]
        assert "Unknown command" in msg

    @pytest.mark.asyncio
    async def test_ignores_non_message_updates(self):
        update = {"update_id": 1, "edited_message": {"text": "/start"}}
        with patch("services.telegram_service.handle_start", new_callable=AsyncMock) as mock:
            await handle_update(update)
        mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_empty_text(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 123},
                "chat": {"id": 123, "type": "private"},
                "text": "",
            },
        }
        with patch("services.telegram_service.handle_start", new_callable=AsyncMock) as mock:
            await handle_update(update)
        mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_plain_text_ignored(self):
        """Non-command text is silently ignored."""
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 123},
                "chat": {"id": 123, "type": "private"},
                "text": "hello world",
            },
        }
        with patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send:
            await handle_update(update)
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_botname_suffix_stripped(self):
        """Commands with @botname suffix are handled correctly."""
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 456},
                "chat": {"id": 456, "type": "private"},
                "text": "/analyze@SmIA_bot Plaud Note",
            },
        }
        with patch("services.telegram_service.handle_analyze", new_callable=AsyncMock) as mock:
            await handle_update(update)
        mock.assert_called_once_with(456, 456, "Plaud Note")


# ---------------------------------------------------------------------------
# Database service function tests
# ---------------------------------------------------------------------------


class TestDatabaseServiceFunctions:
    def test_save_report_service(self):
        from services.database import save_report_service

        mock_response = MagicMock()
        mock_response.data = [{"id": "r-1", "user_id": "uid-1", "topic": "test"}]

        with patch("services.database.get_supabase_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

            result = save_report_service({"topic": "test"}, "uid-1")

        assert result["id"] == "r-1"
        mock_client.table.assert_called_once_with("analysis_reports")

    def test_get_recent_reports_by_user(self):
        from services.database import get_recent_reports_by_user

        mock_response = MagicMock()
        mock_response.data = [
            {"id": "r1", "topic": "Topic 1"},
            {"id": "r2", "topic": "Topic 2"},
        ]

        with patch("services.database.get_supabase_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            (
                mock_client.table.return_value
                .select.return_value
                .eq.return_value
                .order.return_value
                .limit.return_value
                .execute.return_value
            ) = mock_response

            result = get_recent_reports_by_user("uid-1", limit=5)

        assert len(result) == 2
        assert result[0]["id"] == "r1"


# ---------------------------------------------------------------------------
# send_message / send_typing_action tests
# ---------------------------------------------------------------------------


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_sends_message_and_returns_json(self):
        with patch("services.telegram_service.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"ok": True}
            mock_resp.raise_for_status = MagicMock()
            mock_instance.post = AsyncMock(return_value=mock_resp)
            result = await send_message(12345, "Hello!")
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_sends_typing_action(self):
        with patch("services.telegram_service.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post = AsyncMock()
            # send_typing_action swallows exceptions — just ensure it returns None
            result = await send_typing_action(12345)
        assert result is None

    @pytest.mark.asyncio
    async def test_sends_typing_action_swallows_exception(self):
        """Lines 71-72: exception inside the async-with block is swallowed."""
        with patch("services.telegram_service.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post = AsyncMock(side_effect=Exception("timeout"))
            # Must not raise
            result = await send_typing_action(12345)
        assert result is None


# ---------------------------------------------------------------------------
# _parse_topic_and_time_range tests
# ---------------------------------------------------------------------------


class TestParseTopic:
    def test_extracts_valid_time_range(self):
        topic, time_range = _parse_topic_and_time_range("plaud month")
        assert topic == "plaud"
        assert time_range == "month"

    def test_defaults_to_week(self):
        topic, time_range = _parse_topic_and_time_range("plaud")
        assert topic == "plaud"
        assert time_range == "week"

    def test_invalid_time_range_stays_in_topic(self):
        topic, time_range = _parse_topic_and_time_range("plaud quarterly")
        assert topic == "plaud quarterly"
        assert time_range == "week"


# ---------------------------------------------------------------------------
# handle_analyze — additional coverage
# ---------------------------------------------------------------------------


class TestHandleAnalyzeExtra:
    @pytest.mark.asyncio
    async def test_no_binding_sends_error(self):
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=None),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_analyze(chat_id=12345, telegram_user_id=99999, topic="bitcoin")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "bind" in msg.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_sends_error(self):
        binding = {"user_id": "uid-rate"}

        # check_rate_limit is imported inline inside handle_analyze:
        #   from core.rate_limit import check_rate_limit
        # We patch the function on its source module so the inline import
        # picks up the mock when Python resolves the attribute.
        import core.rate_limit as rl_module

        original = rl_module.check_rate_limit
        rl_module.check_rate_limit = lambda user_id: (False, 0)
        try:
            with (
                patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
                patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
            ):
                await handle_analyze(chat_id=12345, telegram_user_id=99999, topic="bitcoin")
        finally:
            rl_module.check_rate_limit = original
        last_msg = mock_send.call_args[0][1]
        assert "limit" in last_msg.lower() or "daily" in last_msg.lower()


# ---------------------------------------------------------------------------
# handle_digest tests
# ---------------------------------------------------------------------------


class TestHandleDigest:
    @pytest.mark.asyncio
    async def test_no_binding_sends_error(self):
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=None),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_digest(chat_id=12345, telegram_user_id=99999)
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "bind" in msg.lower() or "Please" in msg

    @pytest.mark.asyncio
    async def test_no_access_sends_error(self):
        binding = {"user_id": "uid-1", "access_token": "tok"}
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.get_digest_access_status", return_value="none"),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_digest(chat_id=12345, telegram_user_id=99999)
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "access" in msg.lower() or "No digest" in msg

    @pytest.mark.asyncio
    async def test_completed_digest_sends_summary(self):
        binding = {"user_id": "uid-1", "access_token": "tok"}
        digest_data = {
            "executive_summary": "Great AI news today.",
            "top_highlights": ["Highlight one", "Highlight two"],
            "total_items": 42,
            "category_counts": {"AI": 20, "Tech": 22},
        }
        claim_result = {
            "status": "completed",
            "claimed": False,
            "digest_id": "d-abc",
            "digest": digest_data,
        }
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.get_digest_access_status", return_value="approved"),
            patch("services.digest_service.claim_or_get_digest", return_value=claim_result),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_digest(chat_id=12345, telegram_user_id=99999, topic="ai")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "42" in msg or "Digest" in msg

    @pytest.mark.asyncio
    async def test_claimed_runs_pipeline(self):
        binding = {"user_id": "uid-1", "access_token": "tok"}
        claim_result = {
            "status": "collecting",
            "claimed": True,
            "digest_id": "d-new",
        }
        mock_run_digest = AsyncMock()
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.get_digest_access_status", return_value="approved"),
            patch("services.digest_service.claim_or_get_digest", return_value=claim_result),
            patch("services.digest_service.run_digest", mock_run_digest),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_digest(chat_id=12345, telegram_user_id=99999, topic="ai")
        assert mock_send.call_count >= 1
        first_msg = mock_send.call_args_list[0][0][1]
        assert "generat" in first_msg.lower() or "digest" in first_msg.lower()
        mock_run_digest.assert_called_once_with("d-new", topic="ai")

    @pytest.mark.asyncio
    async def test_in_progress_sends_wait_message(self):
        binding = {"user_id": "uid-1", "access_token": "tok"}
        claim_result = {
            "status": "analyzing",
            "claimed": False,
            "digest_id": "d-prog",
        }
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.get_digest_access_status", return_value="approved"),
            patch("services.digest_service.claim_or_get_digest", return_value=claim_result),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_digest(chat_id=12345, telegram_user_id=99999, topic="ai")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "being generated" in msg.lower() or "progress" in msg.lower() or "wait" in msg.lower() or "generated" in msg.lower()

    @pytest.mark.asyncio
    async def test_unknown_status_sends_unavailable(self):
        binding = {"user_id": "uid-1", "access_token": "tok"}
        claim_result = {
            "status": "failed",
            "claimed": False,
            "digest_id": "d-fail",
        }
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.get_digest_access_status", return_value="approved"),
            patch("services.digest_service.claim_or_get_digest", return_value=claim_result),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_digest(chat_id=12345, telegram_user_id=99999, topic="ai")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "unavailable" in msg.lower() or "issue" in msg.lower()

    @pytest.mark.asyncio
    async def test_exception_sends_error(self):
        binding = {"user_id": "uid-1", "access_token": "tok"}
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.get_digest_access_status", return_value="approved"),
            patch("services.digest_service.claim_or_get_digest", side_effect=Exception("DB error")),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_digest(chat_id=12345, telegram_user_id=99999, topic="ai")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "failed" in msg.lower() or "error" in msg.lower() or "try again" in msg.lower()

    @pytest.mark.asyncio
    async def test_claimed_pipeline_exception_logged(self):
        """Lines 460-463: run_digest raises → exception is caught and logged, not re-raised."""
        binding = {"user_id": "uid-1", "access_token": "tok"}
        claim_result = {
            "status": "collecting",
            "claimed": True,
            "digest_id": "d-crash",
        }
        failing_run = AsyncMock(side_effect=Exception("pipeline boom"))
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=binding),
            patch("services.telegram_service.get_digest_access_status", return_value="approved"),
            patch("services.digest_service.claim_or_get_digest", return_value=claim_result),
            patch("services.digest_service.run_digest", failing_run),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            # Must not raise even though run_digest fails
            await handle_digest(chat_id=12345, telegram_user_id=99999, topic="ai")
        # "Generating..." message was still sent
        assert mock_send.call_count >= 1


# ---------------------------------------------------------------------------
# handle_bind — exception path
# ---------------------------------------------------------------------------


class TestHandleBindExtra:
    @pytest.mark.asyncio
    async def test_bind_exception_sends_error(self):
        mock_binding_data = {"user_id": "uid", "bind_code": "ABC123"}
        with (
            patch("services.telegram_service.get_binding_by_telegram_id", return_value=None),
            patch("services.telegram_service.lookup_bind_code", return_value=mock_binding_data),
            patch("services.telegram_service.complete_binding", side_effect=Exception("DB crash")),
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            await handle_bind(chat_id=12345, telegram_user_id=99999, code="ABC123")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "failed" in msg.lower() or "link" in msg.lower()


# ---------------------------------------------------------------------------
# handle_update — additional routing coverage
# ---------------------------------------------------------------------------


def _make_update(text: str, user_id: int = 123, chat_id: int = 123) -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "from": {"id": user_id},
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
        },
    }


class TestHandleUpdateExtra:
    @pytest.mark.asyncio
    async def test_routes_help_command(self):
        with patch("services.telegram_service.handle_help", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/help"))
        mock.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_routes_analyze_command(self):
        with patch("services.telegram_service.handle_analyze", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/analyze bitcoin", user_id=456, chat_id=456))
        mock.assert_called_once_with(456, 456, "bitcoin")

    @pytest.mark.asyncio
    async def test_routes_bind_command(self):
        with patch("services.telegram_service.handle_bind", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/bind CODE123", user_id=789, chat_id=789))
        mock.assert_called_once_with(789, 789, "CODE123")

    @pytest.mark.asyncio
    async def test_routes_digest_command(self):
        with patch("services.telegram_service.handle_digest", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/digest"))
        mock.assert_called_once_with(123, 123, topic="ai")

    @pytest.mark.asyncio
    async def test_routes_digest_geo(self):
        with patch("services.telegram_service.handle_digest", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/digest_geo"))
        mock.assert_called_once_with(123, 123, topic="geopolitics")

    @pytest.mark.asyncio
    async def test_routes_history_command(self):
        with patch("services.telegram_service.handle_history", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/history"))
        mock.assert_called_once_with(123, 123)

    @pytest.mark.asyncio
    async def test_unknown_command_sends_error(self):
        with patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send:
            await handle_update(_make_update("/unknown"))
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][1]
        assert "Unknown command" in msg

    @pytest.mark.asyncio
    async def test_routes_digest_ai(self):
        """Line 626: /digest_ai routes to handle_digest with topic='ai'."""
        with patch("services.telegram_service.handle_digest", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/digest_ai"))
        mock.assert_called_once_with(123, 123, topic="ai")

    @pytest.mark.asyncio
    async def test_routes_digest_climate(self):
        """Line 630: /digest_climate routes to handle_digest with topic='climate'."""
        with patch("services.telegram_service.handle_digest", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/digest_climate"))
        mock.assert_called_once_with(123, 123, topic="climate")

    @pytest.mark.asyncio
    async def test_routes_digest_health(self):
        """Line 632: /digest_health routes to handle_digest with topic='health'."""
        with patch("services.telegram_service.handle_digest", new_callable=AsyncMock) as mock:
            await handle_update(_make_update("/digest_health"))
        mock.assert_called_once_with(123, 123, topic="health")


# ---------------------------------------------------------------------------
# notify_digest_ready tests
# ---------------------------------------------------------------------------


class TestNotifyDigestReady:
    @pytest.mark.asyncio
    async def test_sends_to_all_bound_users(self):
        with (
            patch("services.telegram_service.get_supabase_client") as mock_supabase,
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            admins_resp = MagicMock()
            admins_resp.data = [{"user_id": "user-1"}]
            auth_resp = MagicMock()
            auth_resp.data = [{"user_id": "user-2"}]
            bindings_resp = MagicMock()
            bindings_resp.data = [{"telegram_user_id": 111}, {"telegram_user_id": 222}]

            def table_side_effect(name):
                t = MagicMock()
                if name == "admins":
                    t.select.return_value.execute.return_value = admins_resp
                elif name == "digest_authorized_users":
                    t.select.return_value.execute.return_value = auth_resp
                elif name == "user_bindings":
                    sel = MagicMock()
                    sel.in_.return_value.not_.is_.return_value.execute.return_value = bindings_resp
                    t.select.return_value = sel
                return t

            mock_client.table.side_effect = table_side_effect

            await notify_digest_ready(
                total_items=10,
                categories={"AI": 5, "Tech": 5},
                summary="Great digest",
                topic_name="AI Daily Digest",
            )

        assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_no_users_returns_early(self):
        with (
            patch("services.telegram_service.get_supabase_client") as mock_supabase,
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            admins_resp = MagicMock()
            admins_resp.data = []
            auth_resp = MagicMock()
            auth_resp.data = []

            def table_side_effect(name):
                t = MagicMock()
                if name == "admins":
                    t.select.return_value.execute.return_value = admins_resp
                elif name == "digest_authorized_users":
                    t.select.return_value.execute.return_value = auth_resp
                return t

            mock_client.table.side_effect = table_side_effect

            await notify_digest_ready(total_items=5, categories={})

        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_bindings_returns_early(self):
        with (
            patch("services.telegram_service.get_supabase_client") as mock_supabase,
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            admins_resp = MagicMock()
            admins_resp.data = [{"user_id": "user-1"}]
            auth_resp = MagicMock()
            auth_resp.data = []
            bindings_resp = MagicMock()
            bindings_resp.data = []

            def table_side_effect(name):
                t = MagicMock()
                if name == "admins":
                    t.select.return_value.execute.return_value = admins_resp
                elif name == "digest_authorized_users":
                    t.select.return_value.execute.return_value = auth_resp
                elif name == "user_bindings":
                    sel = MagicMock()
                    sel.in_.return_value.not_.is_.return_value.execute.return_value = bindings_resp
                    t.select.return_value = sel
                return t

            mock_client.table.side_effect = table_side_effect

            await notify_digest_ready(total_items=5, categories={})

        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_send_failure(self):
        """If one send_message raises, continues to next user without crashing."""
        with (
            patch("services.telegram_service.get_supabase_client") as mock_supabase,
            patch("services.telegram_service.send_message", new_callable=AsyncMock) as mock_send,
        ):
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            admins_resp = MagicMock()
            admins_resp.data = [{"user_id": "user-1"}]
            auth_resp = MagicMock()
            auth_resp.data = [{"user_id": "user-2"}]
            bindings_resp = MagicMock()
            bindings_resp.data = [{"telegram_user_id": 111}, {"telegram_user_id": 222}]

            def table_side_effect(name):
                t = MagicMock()
                if name == "admins":
                    t.select.return_value.execute.return_value = admins_resp
                elif name == "digest_authorized_users":
                    t.select.return_value.execute.return_value = auth_resp
                elif name == "user_bindings":
                    sel = MagicMock()
                    sel.in_.return_value.not_.is_.return_value.execute.return_value = bindings_resp
                    t.select.return_value = sel
                return t

            mock_client.table.side_effect = table_side_effect

            # First call raises, second should still succeed
            mock_send.side_effect = [Exception("Network error"), None]

            # Should not raise
            await notify_digest_ready(total_items=5, categories={"AI": 5})

        # Called twice even though first raised
        assert mock_send.call_count == 2
