"""
NODE: Post to RU
PURPOSE: Posts the Russian translation to @aiflowdaily_ru channel.
         Swaps EN signature for RU signature.
         Downloads and resizes image if needed (matching n8n behavior).
INPUT: {ru_post_text, creative_type, creative_url}
OUTPUT: Success/failure
"""

import requests as sync_requests
from io import BytesIO
from PIL import Image

from utils.config import TELEGRAM_BOT_TOKEN, RU_CHANNEL_ID, EN_SIGNATURE, RU_SIGNATURE
from utils.logger import log_info, log_error
from utils.telegram_error import send_error


def _swap_signature(text: str) -> str:
    """Replace EN channel link with RU channel link."""
    return text.replace(
        '<a href="https://t.me/aiflowdaily"><b>AI Flow Daily</b></a>',
        '<a href="https://t.me/aiflowdaily_ru"><b>AI Flow Daily</b></a>',
    )


def _download_and_resize(image_url: str, max_size: int = 2000) -> BytesIO | None:
    """Download image and resize to max dimensions (matching n8n Resize node)."""
    try:
        resp = sync_requests.get(
            image_url,
            timeout=30,
            headers={
                "Accept": "*/*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        )
        resp.raise_for_status()

        img = Image.open(BytesIO(resp.content))
        img.thumbnail((max_size, max_size), Image.LANCZOS)

        output = BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        output.name = "cover.png"
        return output

    except Exception as e:
        log_error(f"[RU Post] Image download/resize failed: {e}")
        return None


async def execute(bot, ru_post_text: str, creative_type: str, creative_url: str) -> bool:
    """
    Post RU translation to the Russian channel.

    Args:
        bot: telegram.Bot instance
        ru_post_text: Russian post text (HTML)
        creative_type: "video"|"image"|"none"
        creative_url: URL or "none"

    Returns:
        True on success, False on failure
    """
    try:
        # Swap signature
        post_text = _swap_signature(ru_post_text)

        if creative_type == "video" and creative_url and creative_url != "none":
            await bot.send_video(
                chat_id=RU_CHANNEL_ID,
                video=creative_url,
                caption=post_text,
                parse_mode="HTML",
            )
        elif creative_type == "image" and creative_url and creative_url != "none":
            # Download and resize image (matching n8n Resize1 node)
            photo = _download_and_resize(creative_url)
            if photo:
                await bot.send_photo(
                    chat_id=RU_CHANNEL_ID,
                    photo=photo,
                    caption=post_text,
                    parse_mode="HTML",
                )
            else:
                # Fallback: send as URL
                await bot.send_photo(
                    chat_id=RU_CHANNEL_ID,
                    photo=creative_url,
                    caption=post_text,
                    parse_mode="HTML",
                )
        else:
            await bot.send_message(
                chat_id=RU_CHANNEL_ID,
                text=post_text,
                parse_mode="HTML",
            )

        log_info("[RU Post] ✓ Posted to Russian channel")
        return True

    except Exception as e:
        log_error(f"[RU Post] Error: {e}")
        send_error(str(e), node_name="post_to_ru")
        return False
