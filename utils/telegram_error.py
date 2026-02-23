"""
UTIL: Telegram Error Notifier
PURPOSE: Sends error alerts to admin Telegram channel for monitoring.
"""

import requests
from utils.config import TELEGRAM_BOT_TOKEN, ADMIN_CHANNEL_ID
from utils.logger import log_error

PROJECT_NAME = "AI Flow Daily"


def send_error(error_message: str, node_name: str = "Unknown") -> None:
    """Send error notification to Telegram admin channel."""
    text = (
        f"🚨 <b>{PROJECT_NAME}</b>\n"
        f"📍 Node: <code>{node_name}</code>\n"
        f"❌ Error: {error_message[:500]}"
    )

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={
                "chat_id": ADMIN_CHANNEL_ID,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        log_error(f"Failed to send Telegram error alert: {e}")
