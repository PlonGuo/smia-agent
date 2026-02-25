"""Tests for email service."""

import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.email_service import (
    send_access_request_notification,
    send_approval_email,
    send_rejection_email,
)


class TestSendAccessRequestNotification:
    @patch("services.email_service.resend.Emails.send")
    def test_sends_to_all_admins(self, mock_send):
        admin_emails = ["admin1@example.com", "admin2@example.com"]
        send_access_request_notification(
            requester_email="user@example.com",
            reason="I need access for research",
            admin_emails=admin_emails,
        )
        assert mock_send.call_count == 2
        # Verify correct emails
        calls = mock_send.call_args_list
        assert calls[0][0][0]["to"] == "admin1@example.com"
        assert calls[1][0][0]["to"] == "admin2@example.com"
        assert "user@example.com" in calls[0][0][0]["subject"]

    @patch("services.email_service.resend.Emails.send")
    def test_empty_admin_list(self, mock_send):
        send_access_request_notification(
            requester_email="user@example.com",
            reason="I need access",
            admin_emails=[],
        )
        mock_send.assert_not_called()


class TestSendApprovalEmail:
    @patch("services.email_service.resend.Emails.send")
    def test_sends_approval(self, mock_send):
        send_approval_email("user@example.com")
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == "user@example.com"
        assert "approved" in call_args["subject"]


class TestSendRejectionEmail:
    @patch("services.email_service.resend.Emails.send")
    def test_sends_rejection_with_reason(self, mock_send):
        send_rejection_email("user@example.com", reason="Not enough information")
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == "user@example.com"
        assert "Not enough information" in call_args["html"]

    @patch("services.email_service.resend.Emails.send")
    def test_sends_rejection_without_reason(self, mock_send):
        send_rejection_email("user@example.com")
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert "Reason:" not in call_args["html"]

    @patch("services.email_service.resend.Emails.send", side_effect=Exception("API Error"))
    def test_handles_send_failure(self, mock_send):
        # Should not raise, just log
        send_rejection_email("user@example.com")
        mock_send.assert_called_once()
