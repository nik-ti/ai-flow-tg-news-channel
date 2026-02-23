"""
NODE: Summarizer
PURPOSE: Extract the main news event from a raw article, trim to ≤1500 chars,
         and produce a clean title. Runs FIRST in the AI pipeline.
INPUT: {article_text, article_url} from source parser
OUTPUT: {article_title, article_text} (summarized) or None if irrelevant/empty
"""

# ── AI Configuration ─────────────────────────────────────────
MODEL = "google/gemini-2.5-flash"
TEMPERATURE = 0.2
MAX_TOKENS = 2000

PROMPT = """## Article text:
{article_text}"""

SYSTEM_MESSAGE = """## ROLE  
You are an AI news analyst. Your ONLY task is to process AI-related articles: first summarize them, then check relevance.

## TASK  
1. Read the article text.  
2. Identify the single main point: what new thing happened?  
3. If the text is gibberish, too short for analysis, mentions no specific news, or is just an ad/list/tutorial without a clear event → output SKIP.  
4. If you can identify the main news point → output summary + title.

## OUTPUT FORMAT (strict JSON)
If valid:
{
  "article_title": "Short descriptive title of the main event (3-8 words)",
  "article_text": "Summarized text with only the essential facts. Max 1500 characters."
}

If invalid:
{
  "article_title": "SKIP",
  "article_text": "SKIP"
}

## RULES  
- Focus on ONE main news event, ignore tangential details.  
- Keep only the facts relevant to the main point.  
- Remove any promotional text, author bios, ads, newsletter plugs.  
- Keep mentions of specific tools, models, companies, or products.  
- The title should describe the event, not the article (e.g. "OpenAI releases GPT-5" not "A look at the latest AI model").  
- Maximum 1500 characters for article_text.  
- Output ONLY valid JSON, nothing else."""

# ── Implementation ────────────────────────────────────────────
from utils.openrouter_client import chat_completion
from utils.logger import log_info, log_debug
from utils.telegram_error import send_error


def execute(article: dict) -> dict | None:
    """
    Summarize an article's content.

    Args:
        article: {article_text, article_url, ...}

    Returns:
        Updated article with summarized text and title, or None if SKIP.
    """
    try:
        prompt = PROMPT.format(article_text=article["article_text"][:8000])

        result = chat_completion(
            prompt=prompt,
            system_message=SYSTEM_MESSAGE,
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=True,
        )

        title = result.get("article_title", "SKIP")
        text = result.get("article_text", "SKIP")

        if title == "SKIP" or text == "SKIP":
            log_info(f"[Summarizer] Skipped: {article['article_url']}")
            return None

        article["article_title"] = title
        article["article_text"] = text
        log_info(f"[Summarizer] ✓ {title}")
        return article

    except Exception as e:
        log_info(f"[Summarizer] Error: {e}")
        send_error(str(e), node_name="summarizer")
        return None


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    test_article = {
        "article_text": "GitHub has opened up the internal agent runtime that powers GitHub Copilot CLI and exposed it as a programmable SDK. The GitHub Copilot-SDK, now in technical preview, lets you embed the same agentic execution loop into any application.",
        "article_url": "https://example.com/test",
    }
    result = execute(test_article)
    if result:
        print(f"Title: {result['article_title']}")
        print(f"Text: {result['article_text']}")
    else:
        print("SKIPPED")
