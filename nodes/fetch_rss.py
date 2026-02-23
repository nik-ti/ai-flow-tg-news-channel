"""
NODE: Fetch RSS Feeds
PURPOSE: Polls RSS feeds (marktechpost, techcrunch, theverge), parses new articles
         via AI parser microservice, and normalizes output.
INPUT: None (triggered by scheduler)
OUTPUT: List of article dicts: {article_text, article_url, article_date, images, videos}
DEPENDENCIES: feedparser, requests
"""

import ssl
import certifi
import feedparser
import requests
from datetime import datetime, timezone

# Fix macOS SSL certificate issue for feedparser/urllib
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

from utils.config import RSS_FEEDS, AI_PARSER_URL, TAVILY_API_KEY
from utils.logger import log_info, log_error, log_debug
from utils.telegram_error import send_error
from utils import notion_client


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
                "images": [],
                "videos": [],
            }
        return None
    except Exception as e:
        log_error(f"Tavily extract failed for {article_url}: {e}")
        return None


def _parse_article_detail(article_url: str) -> dict | None:
    """Call AI parser to get full article content."""
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
        log_error(f"Parser returned error for {article_url}: {error_msg}")
        send_error(f"Parser failed for {article_url}: {error_msg}", node_name="fetch_rss")
        return None
    except Exception as e:
        log_error(f"AI parser failed for {article_url}: {e}")
        send_error(f"Parser API failed (502/Crash) for {article_url}: {e}", node_name="fetch_rss_api")
        return None


def _normalize_rss_article(entry: dict, source_name: str) -> dict | None:
    """
    Process a single RSS entry:
    1. Check Notion for URL dedup
    2. Parse via AI parser for full text + images/videos
    3. Return normalized payload
    """
    article_url = entry.get("link", "")

    if not article_url:
        return None

    # URL-based dedup
    if notion_client.url_exists(article_url):
        log_debug(f"[{source_name}] Already in Notion: {article_url}")
        return None

    log_info(f"[{source_name}] New article: {article_url}")

    # For marktechpost, we can use content:encoded from RSS
    # but still call parser for images/videos
    rss_text = ""
    if source_name == "marktechpost":
        rss_text = entry.get("content", [{}])[0].get("value", "")
        if not rss_text:
            rss_text = entry.get("summary", "")

    # Parse via AI parser for full text + images/videos
    parsed = _parse_article_detail(article_url)

    article_text = ""
    images = []
    videos = []

    if parsed:
        article_text = parsed.get("full_text", "")
        images = parsed.get("images", [])
        videos = parsed.get("videos", [])

    # Fallback: Use Tavily if parser failed for major sources
    if not article_text and not rss_text and source_name in ["techcrunch", "theverge"]:
        log_info(f"[{source_name}] Parser failed, trying Tavily fallback")
        tavily_data = _tavily_extract(article_url)
        if tavily_data:
            article_text = tavily_data.get("full_text", "")

    # Fallback: use RSS content if parser didn't get text
    if not article_text and rss_text:
        article_text = rss_text

    if not article_text:
        log_debug(f"[{source_name}] No text extracted for {article_url}")
        return None

    return {
        "article_text": article_text,
        "article_url": article_url,
        "article_date": datetime.now(timezone.utc).isoformat(),
        "images": images if images else [],
        "videos": videos if videos else [],
        "source": source_name,
    }


def execute() -> list[dict]:
    """
    Fetch and process all RSS feeds.
    Returns list of normalized article payloads.
    """
    articles = []

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            log_info(f"Fetching RSS: {source_name}")
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                log_error(f"RSS feed error for {source_name}: {feed.bozo_exception}")
                continue

            # Process the latest 5 entries to avoid missing articles published closely together.
            # Deduplication against Notion prevents reprocessing old ones.
            for entry in feed.entries[:5]:
                result = _normalize_rss_article(entry, source_name)
                if result:
                    articles.append(result)

        except Exception as e:
            log_error(f"[{source_name}] RSS fetch failed: {e}")
            send_error(str(e), node_name="fetch_rss")

    log_info(f"RSS feeds: {len(articles)} new article(s) found")
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
