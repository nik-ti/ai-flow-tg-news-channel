"""
UTIL: Notion Client
PURPOSE: Wrapper around Notion API for article tracking.
         Handles querying, creating, and updating database pages.
DEPENDENCIES: notion-client
"""

from datetime import datetime, timedelta, timezone
from notion_client import Client
from utils.config import NOTION_TOKEN, NOTION_DATABASE_ID
from utils.logger import log_info, log_error, log_debug

notion = Client(auth=NOTION_TOKEN)


# ── Query helpers ────────────────────────────────────────────


def url_exists(article_url: str) -> bool:
    """Check if an article URL already exists in the database."""
    try:
        result = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "Source URL",
                "url": {"equals": article_url},
            },
        )
        return len(result.get("results", [])) > 0
    except Exception as e:
        log_error(f"Notion url_exists check failed: {e}")
        return False


def get_recent_articles(days: int = 3) -> list[dict]:
    """
    Get recent articles from the database (for duplicate checking).
    Returns list of {title, source_url, post_text} dicts.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        result = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "and": [
                    {
                        "property": "Article date",
                        "date": {"after": cutoff},
                    },
                    {
                        "property": "Type",
                        "select": {"does_not_equal": "Tool"},
                    },
                ]
            },
        )

        articles = []
        for page in result.get("results", []):
            props = page.get("properties", {})

            # Extract title
            title_prop = props.get("Title", {})
            title = ""
            if title_prop.get("title"):
                title = title_prop["title"][0]["text"]["content"]

            # Extract source URL
            source_url = props.get("Source URL", {}).get("url", "")

            # Extract post text
            post_text = ""
            post_text_prop = props.get("Post text", {})
            if post_text_prop.get("rich_text"):
                post_text = post_text_prop["rich_text"][0]["text"]["content"]

            articles.append({
                "title": title,
                "source_url": source_url,
                "post_text": post_text,
            })

        return articles
    except Exception as e:
        log_error(f"Notion get_recent_articles failed: {e}")
        return []


# ── Create / Update ──────────────────────────────────────────


def create_article_page(
    title: str,
    article_url: str,
    creative_url: str,
    post_text: str,
    why_relevant: str,
    status: str = "Sent for approval",
) -> str | None:
    """
    Create a new page in the Notion database.
    Returns the page ID on success, None on failure.
    """
    try:
        properties = {
            "Title": {"title": [{"text": {"content": title}}]},
            "Article date": {"date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%d")}},
            "Source URL": {"url": article_url},
            "Post text": {"rich_text": [{"text": {"content": post_text[:2000]}}]},
            "Why relevant": {"rich_text": [{"text": {"content": why_relevant[:2000]}}]},
            "Status": {"status": {"name": status}},
            "Type": {"select": {"name": "News"}},
        }

        if creative_url and creative_url != "none":
            properties["Creative url"] = {"url": creative_url}

        result = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties,
        )

        page_id = result["id"]
        log_info(f"Created Notion page: {title} ({page_id})")
        return page_id

    except Exception as e:
        log_error(f"Notion create_article_page failed: {e}")
        return None


def update_page_status(page_id: str, status: str, post_url: str = "") -> bool:
    """Update page status (Posted / Declined) and optionally set post URL."""
    try:
        properties = {
            "Status": {"status": {"name": status}},
        }

        if post_url:
            properties["post_url"] = {
                "rich_text": [{"text": {"content": post_url}}]
            }

        notion.pages.update(page_id=page_id, properties=properties)
        log_info(f"Updated Notion page {page_id}: status={status}")
        return True

    except Exception as e:
        log_error(f"Notion update_page_status failed: {e}")
        return False


def get_article_data(page_id: str) -> dict | None:
    """
    Fetch article data from a Notion page.
    Used for stateless approval flow (recovering data from Page ID).
    """
    try:
        page = notion.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})

        # Extract fields
        title = ""
        title_prop = props.get("Title", {})
        if title_prop.get("title"):
            title = title_prop["title"][0]["text"]["content"]

        post_text = ""
        post_text_prop = props.get("Post text", {})
        if post_text_prop.get("rich_text"):
            post_text = post_text_prop["rich_text"][0]["text"]["content"]

        creative_url = "none"
        creative_prop = props.get("Creative url", {})
        if creative_prop.get("url"):
            creative_url = creative_prop["url"]

        status = "Unknown"
        status_prop = props.get("Status", {})
        if status_prop.get("status"):
            status = status_prop["status"]["name"]

        article_url = ""
        url_prop = props.get("Source URL", {})
        if url_prop.get("url"):
            article_url = url_prop["url"]

        return {
            "title": title,
            "post_text": post_text,
            "creative_url": creative_url,
            "status": status,
            "article_url": article_url,
            "page_id": page_id,
        }

    except Exception as e:
        log_error(f"Notion get_article_data failed: {e}")
        return None
