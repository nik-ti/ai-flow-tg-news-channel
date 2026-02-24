"""
NODE: Post to Telegram
PURPOSE: Admin preview → approval (inline buttons) → post to main channel.
         Uses python-telegram-bot with callback queries for Approve/Decline.
INPUT: {post_text, creative_type, creative_url, notion_page_id, article_title}
OUTPUT: {approved: bool, post_url: str, message_id: int} or None

NOTE: This node is designed to be called from main.py where the Telegram
      Application is running. The approval flow uses a pending_posts dict
      to track posts awaiting approval.
"""

import asyncio
import requests as sync_requests
from io import BytesIO
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.config import TELEGRAM_BOT_TOKEN, ADMIN_CHANNEL_ID, MAIN_CHANNEL_ID
from utils.logger import log_info, log_error
from utils.telegram_error import send_error

# ── Shared state for pending approvals ───────────────────────
# Key: unique callback ID, Value: article data dict
pending_posts: dict[str, dict] = {}


def _build_keyboard(callback_id: str) -> InlineKeyboardMarkup:
    """Build Approve/Decline inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{callback_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline:{callback_id}"),
        ]
    ])


async def send_preview(bot, article_data: dict) -> str | None:
    """
    Send post preview to admin channel with Approve/Decline buttons.

    Args:
        bot: telegram.Bot instance
        article_data: {post_text, creative_type, creative_url, notion_page_id, article_title, ...}

    Returns:
        callback_id string (Notion UUID) for tracking, or None on failure
    """
    try:
        # Use Notion Page ID as the Callback ID for stateless persistence
        callback_id = article_data.get("notion_page_id")
        if not callback_id:
            log_error("[Telegram] No notion_page_id found for approval button")
            return None

        keyboard = _build_keyboard(callback_id)

        post_text = article_data["post_text"]
        creative_type = article_data.get("creative_type", "none")
        creative_url = article_data.get("creative_url", "none")

        if creative_type == "video" and creative_url and creative_url != "none":
            await bot.send_video(
                chat_id=ADMIN_CHANNEL_ID,
                video=creative_url,
                caption=post_text,
                parse_mode="HTML",
            )
        elif creative_type == "image" and creative_url and creative_url != "none":
            # Download and send as bytes to bypass Telegram fetch errors
            try:
                img_resp = sync_requests.get(creative_url, timeout=30, headers={
                    "User-Agent": "Mozilla/5.0"
                })
                img_resp.raise_for_status()
                photo_bytes = BytesIO(img_resp.content)
                photo_bytes.name = "preview.jpg"
                await bot.send_photo(
                    chat_id=ADMIN_CHANNEL_ID,
                    photo=photo_bytes,
                    caption=post_text,
                    parse_mode="HTML",
                )
            except Exception as img_err:
                log_error(f"[Telegram] Preview image download failed, trying plain URL or text: {img_err}")
                try:
                    await bot.send_photo(
                        chat_id=ADMIN_CHANNEL_ID,
                        photo=creative_url,
                        caption=post_text,
                        parse_mode="HTML",
                    )
                except Exception as tg_err:
                    log_error(f"[Telegram] Preview photo URL also failed, sending text only: {tg_err}")
                    await bot.send_message(
                        chat_id=ADMIN_CHANNEL_ID,
                        text=f"[Image omitted due to fetch error]\n\n{post_text}",
                        parse_mode="HTML",
                    )
        else:
            await bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=post_text,
                parse_mode="HTML",
            )

        # Send approval message right after the preview
        await bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=f"👆 Approve or decline the post above?\n📰 {article_data.get('article_title', 'Unknown')}",
            reply_markup=keyboard,
        )

        # Store in pending (memory cache)
        pending_posts[callback_id] = article_data
        log_info(f"[Telegram] Preview sent for '{article_data.get('article_title', '')}' (id: {callback_id})")
        return callback_id

    except Exception as e:
        log_error(f"[Telegram] Preview send error: {e}")
        send_error(str(e), node_name="post_to_telegram")
        return None


async def post_to_main_channel(bot, article_data: dict) -> dict | None:
    """
    Post approved content to the main channel.

    Returns:
        {post_url, message_id} or None on failure
    """
    try:
        post_text = article_data["post_text"]
        creative_type = article_data.get("creative_type", "none")
        creative_url = article_data.get("creative_url", "none")

        result = None

        if creative_type == "video" and creative_url and creative_url != "none":
            result = await bot.send_video(
                chat_id=MAIN_CHANNEL_ID,
                video=creative_url,
                caption=post_text,
                parse_mode="HTML",
            )
        elif creative_type == "image" and creative_url and creative_url != "none":
            # Download and send as binary (matching n8n behavior)
            try:
                img_resp = sync_requests.get(creative_url, timeout=30, headers={
                    "User-Agent": "Mozilla/5.0"
                })
                img_resp.raise_for_status()
                photo_bytes = BytesIO(img_resp.content)
                photo_bytes.name = "cover.jpg"
                result = await bot.send_photo(
                    chat_id=MAIN_CHANNEL_ID,
                    photo=photo_bytes,
                    caption=post_text,
                    parse_mode="HTML",
                )
            except Exception as img_err:
                log_error(f"[Telegram] Image download failed, trying URL: {img_err}")
                result = await bot.send_photo(
                    chat_id=MAIN_CHANNEL_ID,
                    photo=creative_url,
                    caption=post_text,
                    parse_mode="HTML",
                )
        else:
            result = await bot.send_message(
                chat_id=MAIN_CHANNEL_ID,
                text=post_text,
                parse_mode="HTML",
            )

        if result:
            message_id = result.message_id
            # Construct post URL: https://t.me/aiflowdaily/{message_id}
            channel_username = str(MAIN_CHANNEL_ID).lstrip("@")
            post_url = f"https://t.me/{channel_username}/{message_id}"
            log_info(f"[Telegram] ✓ Posted to main channel: {post_url}")
            return {"post_url": post_url, "message_id": message_id}

        return None

    except Exception as e:
        log_error(f"[Telegram] Main channel post error: {e}")
        send_error(str(e), node_name="post_to_telegram")
        return None
