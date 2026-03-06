"""Email notifications via Resend API and Gmail SMTP."""

from __future__ import annotations

import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
    commits: list[dict], recipient_emails: list[str]
) -> int:
    """Send a platform update email to all recipients via Gmail SMTP.

    Filters out noise commits. Returns count of emails sent.
    """
    meaningful = _filter_commits(commits)
    if not meaningful or not recipient_emails:
        return 0

    # Build HTML commit list
    commit_items = ""
    for c in meaningful:
        author = c.get("author", "Unknown")
        message = c.get("message", "").split("\n", 1)[0]  # first line only
        sha_short = c.get("id", "")[:7]
        url = c.get("url", "#")
        commit_items += (
            f'<tr>'
            f'<td style="padding:6px 12px 6px 0;font-family:monospace;font-size:13px;">'
            f'<a href="{url}" style="color:#6366f1;text-decoration:none;">{sha_short}</a></td>'
            f'<td style="padding:6px 0;">{message}</td>'
            f'<td style="padding:6px 0 6px 12px;color:#888;font-size:13px;">{author}</td>'
            f'</tr>'
        )

    # Use first commit message as dynamic subject
    first_msg = meaningful[0].get("message", "").split("\n", 1)[0]
    subject = f"SmIA Update: {first_msg}"
    if len(subject) > 78:
        subject = subject[:75] + "..."

    html = (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;'
        'max-width:600px;margin:0 auto;color:#1a1a1a;">'
        '<h2 style="color:#6366f1;margin-bottom:4px;">SmIA Platform Updated</h2>'
        '<p style="color:#555;margin-top:0;">A new version has been deployed with the following changes:</p>'
        '<table style="border-collapse:collapse;width:100%;">'
        f'{commit_items}'
        '</table>'
        '<hr style="border:none;border-top:1px solid #e5e5e5;margin:24px 0;" />'
        '<p style="color:#999;font-size:11px;">'
        'You received this because you have an account on SmIA.'
        '</p>'
        '</div>'
    )

    sent = 0
    for email in recipient_emails:
        try:
            _send_gmail(to=email, subject=subject, html=html)
            sent += 1
        except Exception as exc:
            logger.error("Failed to send update email to %s: %s", email, exc)

    return sent
