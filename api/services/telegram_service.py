"""Telegram bot message formatting and command handling.

This module provides all logic for the SmIA Telegram bot:
- Parsing incoming updates from the Telegram Bot API
- Dispatching commands to handlers
- Formatting analysis results for Telegram
- Sending replies via the Bot API

Designed for serverless (Vercel) — no long-running polling.
Uses httpx to send messages directly via the Telegram HTTP API.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from core.config import settings
from services.database import (
    complete_binding,
    get_binding_by_telegram_id,
    get_recent_reports_by_user,
    lookup_bind_code,
    save_report_service,
)

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"
WEB_APP_URL = "https://smia-agent.vercel.app"


# ---------------------------------------------------------------------------
# Telegram Bot API helpers
# ---------------------------------------------------------------------------


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
) -> dict:
    """Send a text message to a Telegram chat via the Bot API."""
    token = settings.telegram_bot_token.strip()
    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def send_typing_action(chat_id: int) -> None:
    """Send a "typing..." indicator to the chat."""
    token = settings.telegram_bot_token.strip()
    url = f"{TELEGRAM_API.format(token=token)}/sendChatAction"
    payload = {"chat_id": chat_id, "action": "typing"}
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            await client.post(url, json=payload)
        except Exception:
            pass  # non-critical


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------


def format_analysis_result(report: dict, report_id: str | None = None) -> str:
    """Format a TrendReport dict into Telegram-friendly HTML."""
    topic = report.get("topic", "Unknown")
    sentiment = report.get("sentiment", "Neutral")
    score = report.get("sentiment_score", 0.5)
    key_insights = report.get("key_insights", [])
    source_breakdown = report.get("source_breakdown", {})
    processing_time = report.get("processing_time_seconds", 0)

    # Sentiment emoji
    if sentiment == "Positive":
        emoji = "\U0001f60a"  # 😊
    elif sentiment == "Negative":
        emoji = "\U0001f61f"  # 😟
    else:
        emoji = "\U0001f610"  # 😐

    lines = [
        "\U0001f4ca <b>Analysis Complete!</b>",
        "",
        f"\U0001f3af <b>Topic:</b> {_escape_html(topic)}",
        f"{emoji} <b>Sentiment:</b> {sentiment} ({score:.2f}/1.0)",
        "",
    ]

    # Key insights
    if key_insights:
        lines.append("\U0001f4a1 <b>Key Insights:</b>")
        for insight in key_insights[:5]:
            lines.append(f"  \u2022 {_escape_html(insight)}")
        lines.append("")

    # Source breakdown
    if source_breakdown:
        lines.append("\U0001f4c8 <b>Sources analyzed:</b>")
        for src, count in source_breakdown.items():
            lines.append(f"  \u2022 {src.capitalize()}: {count} items")
        lines.append("")

    # Web link
    if report_id:
        lines.append(
            f'\U0001f517 <a href="{WEB_APP_URL}/reports/{report_id}">View full report with charts</a>'
        )
        lines.append("")

    # Timing
    if processing_time:
        lines.append(f"\u23f1\ufe0f Analyzed in {processing_time}s")

    return "\n".join(lines)


def format_history(reports: list[dict]) -> str:
    """Format a list of recent reports for Telegram /history."""
    if not reports:
        return (
            "\U0001f4cb <b>No analysis history</b>\n\n"
            "Run <code>/analyze topic</code> to create your first analysis!"
        )

    lines = ["\U0001f4cb <b>Recent Analyses</b> (last 5)\n"]
    for i, r in enumerate(reports[:5], 1):
        topic = r.get("topic", r.get("query", "Unknown"))
        sentiment = r.get("sentiment", "?")
        report_id = r.get("id", "")
        created = r.get("created_at", "")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                created_str = dt.strftime("%b %d, %H:%M")
            except Exception:
                created_str = created[:10]
        else:
            created_str = ""

        link = f"{WEB_APP_URL}/reports/{report_id}" if report_id else ""
        lines.append(
            f"{i}. <b>{_escape_html(topic)}</b> — {sentiment}"
        )
        if created_str:
            lines.append(f"   {created_str}")
        if link:
            lines.append(f'   <a href="{link}">View report</a>')
        lines.append("")

    return "\n".join(lines)


def format_welcome() -> str:
    """Format the /start welcome message."""
    return (
        "\U0001f916 <b>Welcome to SmIA Bot!</b>\n"
        "\n"
        "I'm your Social Media Intelligence Agent. "
        "I analyze trends across Reddit, YouTube, and Amazon.\n"
        "\n"
        "<b>Commands:</b>\n"
        "/analyze &lt;topic&gt; — Analyze a topic\n"
        "/history — View your last 5 analyses\n"
        "/bind &lt;code&gt; — Link your web account\n"
        "/help — Show this help message\n"
        "\n"
        "\U0001f517 <b>Web Dashboard:</b>\n"
        f"{WEB_APP_URL}\n"
        "\n"
        "\u2139\ufe0f To sync with the web app, generate a bind code "
        "in Settings and use <code>/bind CODE</code> here."
    )


def format_help() -> str:
    """Format the /help message."""
    return (
        "\U0001f4d6 <b>SmIA Bot Commands</b>\n"
        "\n"
        "/analyze &lt;topic&gt; — Analyze a topic across Reddit, YouTube, and Amazon\n"
        "  Example: <code>/analyze Plaud Note reviews</code>\n"
        "\n"
        "/history — Show your last 5 analysis reports\n"
        "\n"
        "/bind &lt;code&gt; — Link your Telegram account to the web dashboard\n"
        "  1. Go to Settings on the web app\n"
        "  2. Click 'Generate Bind Code'\n"
        "  3. Send <code>/bind YOUR_CODE</code> here\n"
        "\n"
        "/help — Show this message\n"
        "\n"
        f'\U0001f310 <a href="{WEB_APP_URL}">Open Web Dashboard</a>'
    )


def format_error(message: str) -> str:
    """Format an error message."""
    return f"\u26a0\ufe0f {message}"


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def handle_start(chat_id: int) -> None:
    """Handle the /start command."""
    await send_message(chat_id, format_welcome())


async def handle_help(chat_id: int) -> None:
    """Handle the /help command."""
    await send_message(chat_id, format_help())


async def handle_analyze(
    chat_id: int,
    telegram_user_id: int,
    topic: str,
) -> None:
    """Handle the /analyze <topic> command."""
    # Check binding
    binding = get_binding_by_telegram_id(telegram_user_id)
    if not binding:
        await send_message(
            chat_id,
            format_error(
                "Please bind your Telegram account first.\n"
                f'Visit <a href="{WEB_APP_URL}/settings">Settings</a> '
                "to generate a bind code, then use <code>/bind CODE</code> here."
            ),
        )
        return

    # Validate topic
    topic = topic.strip()
    if len(topic) < 3:
        await send_message(
            chat_id,
            format_error(
                'Please provide a topic to analyze.\n'
                'Example: <code>/analyze Plaud Note reviews</code>'
            ),
        )
        return

    user_id = binding["user_id"]

    # Rate limit check
    from core.rate_limit import check_rate_limit

    allowed, remaining = check_rate_limit(user_id, source="telegram")
    if not allowed:
        await send_message(
            chat_id,
            format_error(
                "You've reached the hourly limit (10 analyses). "
                "Try again later."
            ),
        )
        return

    # Send typing indicator
    await send_typing_action(chat_id)
    await send_message(
        chat_id,
        "\u23f3 <b>Analyzing...</b> This may take 1-2 minutes.\n"
        f"Topic: <i>{_escape_html(topic)}</i>",
    )

    try:
        # Import here to avoid circular imports
        from services.agent import analyze_topic

        report = await analyze_topic(
            query=topic,
            user_id=user_id,
            source="telegram",
        )

        # Save to database (service-role, no user JWT)
        report_dict = report.model_dump(mode="json")
        saved = save_report_service(report_dict, user_id)
        report_id = saved.get("id")

        # Send formatted result
        await send_message(
            chat_id,
            format_analysis_result(report_dict, report_id),
        )

    except Exception as exc:
        logger.error("Telegram analysis failed for '%s': %s", topic, exc)
        await send_message(
            chat_id,
            format_error(
                "Analysis failed. Some sources may be unavailable.\n"
                "Please try again later."
            ),
        )


async def handle_bind(
    chat_id: int,
    telegram_user_id: int,
    code: str,
) -> None:
    """Handle the /bind <code> command."""
    code = code.strip().upper()

    if len(code) != 6:
        await send_message(
            chat_id,
            format_error(
                "Invalid bind code format. The code should be 6 characters.\n"
                "Generate one at Settings on the web app."
            ),
        )
        return

    # Check if already bound
    existing = get_binding_by_telegram_id(telegram_user_id)
    if existing:
        await send_message(
            chat_id,
            "\u2705 Your Telegram is already linked to a web account.\n"
            "To re-link, unbind first from the web Settings page.",
        )
        return

    # Look up the code
    binding = lookup_bind_code(code)
    if not binding:
        await send_message(
            chat_id,
            format_error(
                "Invalid or expired bind code.\n"
                "Please generate a new code from the web Settings page."
            ),
        )
        return

    # Complete binding
    try:
        complete_binding(bind_code=code, telegram_user_id=telegram_user_id)
        await send_message(
            chat_id,
            "\u2705 <b>Account linked successfully!</b>\n\n"
            "Your Telegram is now connected to your SmIA web account.\n"
            "Use /analyze to start analyzing topics!",
        )
    except Exception as exc:
        logger.error("Binding failed: %s", exc)
        await send_message(
            chat_id,
            format_error("Failed to link accounts. Please try again."),
        )


async def handle_history(
    chat_id: int,
    telegram_user_id: int,
) -> None:
    """Handle the /history command."""
    binding = get_binding_by_telegram_id(telegram_user_id)
    if not binding:
        await send_message(
            chat_id,
            format_error(
                "Please bind your Telegram account first.\n"
                f'Visit <a href="{WEB_APP_URL}/settings">Settings</a> '
                "to generate a bind code."
            ),
        )
        return

    user_id = binding["user_id"]
    reports = get_recent_reports_by_user(user_id, limit=5)
    await send_message(chat_id, format_history(reports))


# ---------------------------------------------------------------------------
# Main update dispatcher
# ---------------------------------------------------------------------------


async def handle_update(update: dict) -> None:
    """Parse a Telegram Update and dispatch to the appropriate handler.

    Expected update structure (subset):
    {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {"id": 67890, "first_name": "User"},
            "chat": {"id": 67890, "type": "private"},
            "text": "/analyze some topic"
        }
    }
    """
    message = update.get("message")
    if not message:
        return  # Ignore non-message updates (edited, callback, etc.)

    text = message.get("text", "").strip()
    if not text:
        return

    chat_id = message["chat"]["id"]
    telegram_user_id = message["from"]["id"]

    # Strip @botname suffix from commands (e.g. /analyze@SmIA_bot topic)
    command = text.split()[0] if text.startswith("/") else ""
    if "@" in command:
        command = command.split("@")[0]

    if command == "/start":
        await handle_start(chat_id)
    elif command == "/help":
        await handle_help(chat_id)
    elif command == "/analyze":
        topic = text[len(text.split()[0]):].strip()
        await handle_analyze(chat_id, telegram_user_id, topic)
    elif command == "/bind":
        code = text[len(text.split()[0]):].strip()
        await handle_bind(chat_id, telegram_user_id, code)
    elif command == "/history":
        await handle_history(chat_id, telegram_user_id)
    elif text.startswith("/"):
        await send_message(
            chat_id,
            format_error(
                "Unknown command. Use /help to see available commands."
            ),
        )
