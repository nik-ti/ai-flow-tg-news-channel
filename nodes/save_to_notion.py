"""
NODE: Save to Notion
PURPOSE: Creates/updates article records in Notion database.
         Wraps utils/notion_client with pipeline-specific logic.
INPUT: Article data + post details from pipeline
OUTPUT: Notion page_id or None
"""

from utils import notion_client
from utils.logger import log_info


def create_row(
    title: str,
    article_url: str,
    creative_url: str,
    post_text: str,
    why_relevant: str,
) -> str | None:
    """Create a new article row in Notion with 'Sent for approval' status."""
    return notion_client.create_article_page(
        title=title,
        article_url=article_url,
        creative_url=creative_url,
        post_text=post_text,
        why_relevant=why_relevant,
        status="Sent for approval",
    )


def mark_posted(page_id: str, post_url: str) -> bool:
    """Update status to 'Posted' and save the Telegram post URL."""
    return notion_client.update_page_status(page_id, "Posted", post_url)


def mark_declined(page_id: str) -> bool:
    """Update status to 'Declined'."""
    return notion_client.update_page_status(page_id, "Declined")


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    page_id = create_row(
        title="Test Article",
        article_url="https://example.com/test-notion",
        creative_url="none",
        post_text="Test post text",
        why_relevant="Testing Notion integration",
    )
    print(f"Created page: {page_id}")
