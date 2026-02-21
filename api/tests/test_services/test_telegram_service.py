"""Tests for the Telegram bot service (message formatting + command handlers)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.telegram_service import (
    _escape_html,
    format_analysis_result,
    format_error,
    format_help,
    format_history,
    format_welcome,
    handle_analyze,
    handle_bind,
    handle_help,
    handle_history,
    handle_start,
    handle_update,
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
        assert "smia-agent.vercel.app" in result


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
