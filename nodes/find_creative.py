"""
NODE: Find Creative
PURPOSE: Determines the best image/video for the post.
         Step 1: Check for video in article data
         Step 2: If no video, call image-finder microservice
INPUT: Original article data with images/videos
OUTPUT: {creative_type, creative_url} — "video"|"image"|"none"
DEPENDENCIES: requests
"""

import requests
from utils.config import IMAGE_FINDER_URL
from utils.logger import log_info, log_error, log_debug
from utils.telegram_error import send_error


def _prepare_images_string(images: list) -> str:
    """Convert images list to comma-separated URL string (matching n8n Prepare images node)."""
    urls = []
    for img in images:
        if isinstance(img, dict):
            url = img.get("url", "")
        elif isinstance(img, str):
            url = img
        else:
            continue
        if url and url.strip():
            urls.append(url.strip())
    return ",".join(urls)


def _find_video(videos: list) -> str | None:
    """Check for valid video (must have URL and description)."""
    if not videos or not isinstance(videos, list):
        return None

    for video in videos:
        if isinstance(video, dict):
            url = video.get("url", "").strip()
            desc = video.get("description", "").strip()
            if url and desc:
                log_info(f"[Creative] Video found: {url}")
                return url
        elif isinstance(video, str) and video.strip():
            log_info(f"[Creative] Video URL found: {video}")
            return video.strip()

    return None


def _find_image(title: str, article_text: str, source_url: str, images: list) -> str | None:
    """Call image-finder microservice to find the best image."""
    try:
        images_str = _prepare_images_string(images)
        images_list = [u for u in images_str.split(",") if u]

        payload = {
            "title": title,
            "research": article_text[:1000],
            "source_url": source_url,
        }
        if images_list:
            payload["images"] = images_list

        log_debug(f"[Creative] Calling image-finder with title='{title}'")
        resp = requests.post(IMAGE_FINDER_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        image_url = data.get("image_url", "")
        if image_url:
            log_info(f"[Creative] Image found: {image_url}")
            return image_url

        log_debug("[Creative] Image finder returned no image")
        return None

    except Exception as e:
        log_error(f"[Creative] Image finder error: {e}")
        return None


def execute(article: dict) -> dict:
    """
    Find the best creative (video or image) for the article.

    Args:
        article: Full article dict with images, videos, article_text, article_title, article_url

    Returns:
        {creative_type: "video"|"image"|"none", creative_url: str}
    """
    try:
        # Step 1: Check for video
        video_url = _find_video(article.get("videos", []))
        if video_url:
            return {"creative_type": "video", "creative_url": video_url}

        # Step 2: Find image via microservice
        image_url = _find_image(
            title=article.get("article_title", ""),
            article_text=article.get("article_text", ""),
            source_url=article.get("article_url", ""),
            images=article.get("images", []),
        )

        if image_url:
            return {"creative_type": "image", "creative_url": image_url}

        # No creative found
        log_info("[Creative] No video or image found, posting text-only")
        return {"creative_type": "none", "creative_url": "none"}

    except Exception as e:
        log_error(f"[Creative] Error: {e}")
        send_error(str(e), node_name="find_creative")
        return {"creative_type": "none", "creative_url": "none"}


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    test = {
        "article_title": "GitHub Releases Copilot SDK",
        "article_text": "GitHub opened up the internal agent runtime...",
        "article_url": "https://www.marktechpost.com/2026/01/23/github-releases-copilot-sdk/",
        "images": [""],
        "videos": [],
    }
    result = execute(test)
    print(f"Type: {result['creative_type']}, URL: {result['creative_url']}")
