"""Email notifications via Resend API."""

from __future__ import annotations

import logging

import resend

from core.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.resend_api_key


def _send_email(to: str, subject: str, html: str) -> None:
    """Low-level sync send. resend.Emails.send() is synchronous (I5)."""
    try:
        resend.Emails.send({
            "from": "SmIA <onboarding@resend.dev>",
            "to": to,
            "subject": subject,
            "html": html,
        })
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)


def send_access_request_notification(
    requester_email: str, reason: str, admin_emails: list[str]
) -> None:
    """Notify all admins about a new access request."""
    for email in admin_emails:
        _send_email(
            to=email,
            subject=f"New AI Daily Report access request from {requester_email}",
            html=(
                f"<p><b>{requester_email}</b> requested access to the AI Daily Report.</p>"
                f"<p>Reason: {reason}</p>"
                f"<p><a href='/admin'>Review in admin panel</a></p>"
            ),
        )


def send_approval_email(user_email: str) -> None:
    """Notify user their access was approved."""
    _send_email(
        to=user_email,
        subject="Your AI Daily Report access has been approved",
        html=(
            "<p>You now have access to the AI Daily Report.</p>"
            "<p><a href='/ai-daily-report'>View today's digest</a></p>"
        ),
    )


def send_rejection_email(user_email: str, reason: str | None = None) -> None:
    """Notify user their access was rejected."""
    reason_html = f"<p>Reason: {reason}</p>" if reason else ""
    _send_email(
        to=user_email,
        subject="AI Daily Report access request update",
        html=(
            f"<p>Your access request was not approved.</p>{reason_html}"
            "<p>You can submit a new request if needed.</p>"
        ),
    )
