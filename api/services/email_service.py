"""Email notifications via Resend API and Gmail SMTP."""

from __future__ import annotations

import html as html_mod
import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import resend

from core.config import settings
from models.update_schemas import UpdateSummary

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


_NOISE_PREFIXES = ("chore:", "docs:", "ci:", "style:", "build:")
_MERGE_PATTERN = re.compile(r"^Merge (pull request|branch) ")


def _filter_commits(commits: list[dict]) -> list[dict]:
    """Remove noise commits (chore, docs, ci, merge commits)."""
    filtered = []
    for c in commits:
        msg = c.get("message", "")
        first_line = msg.split("\n", 1)[0].strip().lower()
        if first_line.startswith(_NOISE_PREFIXES):
            continue
        if _MERGE_PATTERN.match(msg):
            continue
        filtered.append(c)
    return filtered


def _send_gmail(to: str, subject: str, html: str) -> None:
    """Send a single email via Gmail SMTP."""
    gmail_addr = settings.gmail_address.strip()
    gmail_pass = settings.gmail_app_password.strip()
    if not gmail_addr or not gmail_pass:
        logger.error("Gmail credentials not configured, skipping email to %s", to)
        return

    msg = MIMEMultipart("alternative")
    msg["From"] = f"SmIA <{gmail_addr}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_addr, gmail_pass)
        server.sendmail(gmail_addr, to, msg.as_string())


def send_update_notification(
    summary: UpdateSummary, recipient_emails: list[str]
) -> int:
    """Send a platform update email to all recipients via Gmail SMTP.

    Accepts an AI-generated UpdateSummary. Returns count of emails sent.
    """
    if not recipient_emails:
        return 0

    safe_summary = html_mod.escape(summary.summary)
    safe_highlights = "".join(
        f'<li style="margin-bottom:6px;color:#333;">{html_mod.escape(h)}</li>'
        for h in summary.highlights
    )

    subject = f"SmIA Update: {summary.headline}"
    if len(subject) > 78:
        subject = subject[:75] + "..."

    html_body = (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;'
        'max-width:600px;margin:0 auto;color:#1a1a1a;">'
        '<h2 style="color:#6366f1;margin-bottom:4px;">What\'s New in SmIA</h2>'
        f'<p style="color:#333;margin-top:8px;line-height:1.6;">{safe_summary}</p>'
        '<ul style="padding-left:20px;margin:16px 0;">'
        f'{safe_highlights}'
        '</ul>'
        '<hr style="border:none;border-top:1px solid #e5e5e5;margin:24px 0;" />'
        '<p style="color:#999;font-size:11px;">'
        'You received this because you have an account on SmIA.'
        '</p>'
        '</div>'
    )

    gmail_addr = settings.gmail_address.strip()
    gmail_pass = settings.gmail_app_password.strip()
    if not gmail_addr or not gmail_pass:
        logger.error("Gmail credentials not configured, skipping update emails")
        return 0

    sent = 0
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_addr, gmail_pass)
            for addr in recipient_emails:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["From"] = f"SmIA <{gmail_addr}>"
                    msg["To"] = addr
                    msg["Subject"] = subject
                    msg.attach(MIMEText(html_body, "html"))
                    server.sendmail(gmail_addr, addr, msg.as_string())
                    sent += 1
                except Exception as exc:
                    logger.error("Failed to send update email to %s: %s", addr, exc)
    except Exception as exc:
        logger.error("Gmail SMTP connection failed: %s", exc)

    return sent
