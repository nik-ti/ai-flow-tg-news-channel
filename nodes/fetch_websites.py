"""
NODE: Fetch Websites
PURPOSE: Parses website list pages (aibase.com, futuretools.io) via AI parser,
         checks for new articles against Notion DB, then fetches full article content.
         Falls back to Tavily extract if AI parser fails.
INPUT: None (triggered by scheduler)
OUTPUT: List of article dicts: {article_text, article_url, article_date, images, videos}
DEPENDENCIES: requests
"""

import requests
from datetime import datetime, timezone

from utils.config import WEBSITE_SOURCES, AI_PARSER_URL, TAVILY_API_KEY
from utils.logger import log_info, log_error, log_debug
from utils.telegram_error import send_error
from utils import notion_client


def _parse_list_page(list_url: str) -> dict | None:
    """Get list page data via AI parser."""
    try:
        resp = requests.post(
            AI_PARSER_URL,
            json={"url": list_url, "page_type": "list"},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("ok") and data.get("data"):
            return data["data"]

        error_msg = data.get("error", "Unknown parser error")
        log_error(f"Parser list page error for {list_url}: {error_msg}")
        send_error(f"Parser list page failed for {list_url}: {error_msg}", node_name="fetch_websites_list")
        return None
    except Exception as e:
        log_error(f"AI parser list page failed for {list_url}: {e}")
        send_error(f"Parser API (List) failed (Crash) for {list_url}: {e}", node_name="fetch_websites_list_api")
        return None


def _parse_detail_page(article_url: str) -> dict | None:
    """Get article detail via AI parser."""
    try:
        resp = requests.post(
            AI_PARSER_URL,
            json={"url": article_url, "page_type": "detail"},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("ok") and data.get("data"):
            return data["data"]

        error_msg = data.get("error", "Unknown parser error")
        log_error(f"Parser detail page error for {article_url}: {error_msg}")
        send_error(f"Parser detail page failed for {article_url}: {error_msg}", node_name="fetch_websites_detail")
        return None
    except Exception as e:
        log_error(f"AI parser detail page failed for {article_url}: {e}")
        send_error(f"Parser API (Detail) failed (Crash) for {article_url}: {e}", node_name="fetch_websites_detail_api")
        return None


def _tavily_extract(article_url: str) -> dict | None:
    """Fallback: use Tavily to extract article content."""
    if not TAVILY_API_KEY:
        log_debug("Tavily API key not set, skipping fallback")
        return None

    try:
        resp = requests.post(
            "https://api.tavily.com/extract",
            json={"api_key": TAVILY_API_KEY, "urls": [article_url]},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if results:
            return {
                "full_text": results[0].get("raw_content", ""),
                "url": results[0].get("url", article_url),
                "images": [],
                "videos": [],
            }
        return None
    except Exception as e:
        log_error(f"Tavily extract failed for {article_url}: {e}")
        return None


def _process_website(source_name: str, list_url: str) -> dict | None:
    """
    Process a single website source:
    1. Parse the list page to get the latest article URL
    2. Check Notion for URL dedup
    3. Parse the article detail page (with Tavily fallback)
    4. Return normalized payload
    """
    log_info(f"[{source_name}] Parsing list page: {list_url}")

    list_data = _parse_list_page(list_url)
    if not list_data:
        log_debug(f"[{source_name}] List page parse failed")
        return None

    items = list_data.get("items", [])
    if not items:
        log_debug(f"[{source_name}] No items found on list page")
        return None

    # Get the latest article URL
    latest_url = items[0].get("url", "")
    if not latest_url:
        log_debug(f"[{source_name}] No URL in latest item")
        return None

    # URL-based dedup
    if notion_client.url_exists(latest_url):
        log_debug(f"[{source_name}] Already in Notion: {latest_url}")
        return None

    log_info(f"[{source_name}] New article: {latest_url}")

    # Parse article detail
    detail = _parse_detail_page(latest_url)

    article_text = ""
    images = []
    videos = []

    if detail and detail.get("full_text"):
        article_text = detail["full_text"]
        images = detail.get("images", [])
        videos = detail.get("videos", [])
    else:
        # Fallback to Tavily
        log_info(f"[{source_name}] Parser failed, trying Tavily fallback")
        tavily_data = _tavily_extract(latest_url)
        if tavily_data and tavily_data.get("full_text"):
            article_text = tavily_data["full_text"]

    if not article_text:
        log_debug(f"[{source_name}] No text extracted for {latest_url}")
        return None

    return {
        "article_text": article_text,
        "article_url": latest_url,
        "article_date": datetime.now(timezone.utc).isoformat(),
        "images": images if images else [],
        "videos": videos if videos else [],
        "source": source_name,
    }


def execute() -> list[dict]:
    """
    Fetch and process all website sources.
    Returns list of normalized article payloads.
    """
    articles = []

    for source_name, list_url in WEBSITE_SOURCES.items():
        try:
            result = _process_website(source_name, list_url)
            if result:
                articles.append(result)
        except Exception as e:
            log_error(f"[{source_name}] website fetch failed: {e}")
            send_error(str(e), node_name="fetch_websites")

    log_info(f"Website sources: {len(articles)} new article(s) found")
    return articles


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    results = execute()
    for a in results:
        print(f"\n{'='*60}")
        print(f"Source: {a['source']}")
        print(f"URL: {a['article_url']}")
        print(f"Text length: {len(a['article_text'])} chars")
        print(f"Images: {len(a['images'])}, Videos: {len(a['videos'])}")
