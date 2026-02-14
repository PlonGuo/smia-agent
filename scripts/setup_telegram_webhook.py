"""Register the Telegram webhook URL with the Telegram Bot API.

Usage:
    uv run python scripts/setup_telegram_webhook.py

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_URL from local.env.
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load env from project root
env_path = Path(__file__).resolve().parent.parent / "local.env"
load_dotenv(env_path)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")

if not BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not set in local.env")
    sys.exit(1)

if not WEBHOOK_URL:
    print("Error: TELEGRAM_WEBHOOK_URL not set in local.env")
    sys.exit(1)


def set_webhook() -> None:
    """Register the webhook with Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    resp = httpx.post(url, json={"url": WEBHOOK_URL})
    data = resp.json()

    if data.get("ok"):
        print(f"Webhook set successfully: {WEBHOOK_URL}")
        print(f"Description: {data.get('description', '')}")
    else:
        print(f"Failed to set webhook: {data}")
        sys.exit(1)


def get_webhook_info() -> None:
    """Print current webhook info."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    resp = httpx.get(url)
    data = resp.json()

    if data.get("ok"):
        info = data["result"]
        print(f"\nCurrent webhook info:")
        print(f"  URL: {info.get('url', '(not set)')}")
        print(f"  Pending updates: {info.get('pending_update_count', 0)}")
        if info.get("last_error_message"):
            print(f"  Last error: {info['last_error_message']}")
            print(f"  Last error date: {info.get('last_error_date', '?')}")
    else:
        print(f"Failed to get webhook info: {data}")


if __name__ == "__main__":
    print(f"Setting webhook for bot token: ...{BOT_TOKEN[-6:]}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print()

    set_webhook()
    get_webhook_info()
