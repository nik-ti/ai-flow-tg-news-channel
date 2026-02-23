"""
NODE: Duplicate Control
PURPOSE: Two-layer dedup: fast URL check + AI semantic comparison against recent posts.
         Catches same news from different sources (cross-source dedup).
INPUT: {article_text, article_title, article_url} (summarized + relevant)
OUTPUT: article dict (unchanged) or None if duplicate
"""

# ── AI Configuration ─────────────────────────────────────────
MODEL = "google/gemini-2.5-flash"
TEMPERATURE = 0.2
MAX_TOKENS = 1500

PROMPT = """## New article:
Title: {new_title}
Text: {new_text}

## Existing recent posts:
{existing_posts}"""

SYSTEM_MESSAGE = """## ROLE
You are a duplicate detector for an AI news channel.

## TASK
Compare the new article with the list of existing recent posts. Determine if the new article covers THE SAME specific news event as any existing post.

## WHAT COUNTS AS DUPLICATE:
- Same product launch/release (even if from different sources with different wording)
- Same company announcement (e.g. "Google launches X" from both TechCrunch and The Verge)
- Same feature update to the same tool

## WHAT IS NOT DUPLICATE:
- Different news about the SAME company (e.g. "Google launches Gemini 2" vs "Google launches NotebookLM")
- Follow-up articles with genuinely NEW information about a previous event
- Similar TOPICS but different specific announcements (e.g. two different AI coding tools launching)

## OUTPUT FORMAT (strict JSON)
{
  "article": "the new article text (preserved exactly)",
  "is_duplicate": true/false,
  "duplicate_of": "title of the matching existing post, or empty string if not duplicate",
  "reason": "1-sentence explanation"
}

## RULES
- Be strict: only flag as duplicate if it's clearly the SAME specific event
- Different perspectives on the same event = duplicate
- Same company but different products = NOT duplicate
- Output ONLY valid JSON"""

# ── Implementation ────────────────────────────────────────────
from utils.openrouter_client import chat_completion
from utils.logger import log_info, log_debug
from utils.telegram_error import send_error
from utils import notion_client


def execute(article: dict) -> dict | None:
    """
    Check if an article is a duplicate of recent posts.

    Args:
        article: {article_text, article_title, article_url, ...}

    Returns:
        Article unchanged if not duplicate, None if duplicate.
    """
    try:
        # Layer 1: URL check (already done in fetch nodes, but double-check)
        if notion_client.url_exists(article["article_url"]):
            log_info(f"[Dedup] ✗ URL already exists: {article['article_url']}")
            return None

        # Layer 2: AI semantic comparison
        recent = notion_client.get_recent_articles(days=3)

        if not recent:
            log_debug("[Dedup] No recent articles to compare against")
            return article

        # Format existing posts for the prompt
        existing_text = ""
        for i, post in enumerate(recent, 1):
            existing_text += f"\n{i}. Title: {post['title']}\n   Text: {post.get('post_text', '')[:200]}\n"

        prompt = PROMPT.format(
            new_title=article.get("article_title", ""),
            new_text=article["article_text"][:1000],
            existing_posts=existing_text,
        )

        result = chat_completion(
            prompt=prompt,
            system_message=SYSTEM_MESSAGE,
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=True,
        )

        is_duplicate = result.get("is_duplicate", False)
        reason = result.get("reason", "")

        if is_duplicate:
            dup_of = result.get("duplicate_of", "")
            log_info(f"[Dedup] ✗ Duplicate of '{dup_of}': {article.get('article_title', 'Unknown')} — {reason}")
            return None

        log_info(f"[Dedup] ✓ Not duplicate: {article.get('article_title', 'Unknown')}")
        return article

    except Exception as e:
        log_info(f"[Dedup] Error (allowing through): {e}")
        send_error(str(e), node_name="duplicate_control")
        # On error, allow the article through (fail-open)
        return article


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    test = {
        "article_text": "OpenAI just launched a brand new SDK for developers.",
        "article_title": "OpenAI New SDK Launch",
        "article_url": "https://example.com/test-dedup",
    }
    result = execute(test)
    print("UNIQUE" if result else "DUPLICATE")
