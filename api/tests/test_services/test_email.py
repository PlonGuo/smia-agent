"""Tests for email service."""

import sys
from pathlib import Path
from unittest.mock import patch

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


class TestFilterCommits:
    def setup_method(self):
        from services.email_service import _filter_commits
        self._filter_commits = _filter_commits

    def test_keeps_feature_commits(self):
        commits = [{"message": "feat: add feature"}]
        result = self._filter_commits(commits)
        assert result == commits

    def test_filters_chore_commits(self):
        commits = [{"message": "chore: update deps"}]
        result = self._filter_commits(commits)
        assert result == []

    def test_filters_docs_commits(self):
        commits = [{"message": "docs: update readme"}]
        result = self._filter_commits(commits)
        assert result == []

    def test_filters_ci_commits(self):
        commits = [{"message": "ci: fix workflow"}]
        result = self._filter_commits(commits)
        assert result == []

    def test_filters_merge_commits(self):
        commits = [{"message": "Merge pull request #1 from foo/bar"}]
        result = self._filter_commits(commits)
        assert result == []

    def test_filters_merge_branch(self):
        commits = [{"message": "Merge branch 'main'"}]
        result = self._filter_commits(commits)
        assert result == []

    def test_multiline_message(self):
        # Only the first line is checked; "chore:" on subsequent lines doesn't filter
        commits = [{"message": "fix: bug\n\nchore: extra"}]
        result = self._filter_commits(commits)
        assert result == commits


class TestSendUpdateNotification:
    def _make_summary(self):
        from models.update_schemas import UpdateSummary
        return UpdateSummary(
            headline="Test Update",
            summary="Summary text here.",
            highlights=["Fix 1", "Fix 2"],
        )

    def test_empty_recipients_returns_zero(self):
        from services.email_service import send_update_notification
        summary = self._make_summary()
        result = send_update_notification(summary, [])
        assert result == 0

    def test_sends_to_all_recipients(self):
        from unittest.mock import MagicMock, patch

        from services.email_service import send_update_notification
        summary = self._make_summary()
        with patch("services.email_service.smtplib.SMTP_SSL") as mock_smtp_cls, \
             patch("services.email_service.settings") as mock_settings:
            mock_settings.gmail_address = "test@gmail.com"
            mock_settings.gmail_app_password = "pass"
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = send_update_notification(summary, ["a@b.com", "c@d.com"])
            assert result == 2

    def test_no_gmail_credentials_returns_zero(self):
        from unittest.mock import patch

        from services.email_service import send_update_notification
        summary = self._make_summary()
        with patch("services.email_service.settings") as mock_settings:
            mock_settings.gmail_address = ""
            mock_settings.gmail_app_password = "pass"
            result = send_update_notification(summary, ["a@b.com"])
            assert result == 0

    def test_long_headline_truncated(self):
        from unittest.mock import MagicMock, patch

        from models.update_schemas import UpdateSummary
        from services.email_service import send_update_notification
        # "SmIA Update: " is 13 chars + 80 X's = 93 chars total → truncated to 78
        long_headline = "X" * 80
        summary = UpdateSummary(
            headline=long_headline,
            summary="Summary text here.",
            highlights=["Fix 1"],
        )
        with patch("services.email_service.smtplib.SMTP_SSL") as mock_smtp_cls, \
             patch("services.email_service.settings") as mock_settings:
            mock_settings.gmail_address = "test@gmail.com"
            mock_settings.gmail_app_password = "pass"
            mock_server = MagicMock()
            captured_subjects = []

            def fake_sendmail(from_addr, to_addr, msg_str):
                # Extract Subject from the raw message string
                for line in msg_str.splitlines():
                    if line.startswith("Subject:"):
                        captured_subjects.append(line[len("Subject:"):].strip())
                        break

            mock_server.sendmail.side_effect = fake_sendmail
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            send_update_notification(summary, ["a@b.com"])
            assert len(captured_subjects) == 1
            assert len(captured_subjects[0]) <= 78
