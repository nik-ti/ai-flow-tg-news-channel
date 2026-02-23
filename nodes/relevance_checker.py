"""
NODE: Relevance Checker
PURPOSE: Determines if an article is relevant for the AI news channel.
         Filters out hardware, corporate news, general guides, etc.
INPUT: {article_text, article_title, article_url} (summarized)
OUTPUT: article dict with added 'relevance_reason' field, or None if not relevant
"""

# ── AI Configuration ─────────────────────────────────────────
MODEL = "openai/gpt-4.1-mini"
TEMPERATURE = 0.3
MAX_TOKENS = 1500

PROMPT = """## Article text:
{article_text}"""

SYSTEM_MESSAGE = """## ROLE
You are a relevance filter for an AI-focused Telegram channel called AI Flow Daily (short: AIF). AIF covers tools and tech that help people work with AI.

## WHAT IS RELEVANT (post it):
- New AI tools, apps, or platforms people can USE
- Major updates to existing AI tools (new features, pricing changes, API releases)
- AI model releases that developers/users can access (new LLMs, image models, etc.)
- SDKs, APIs, frameworks for building with AI
- AI integrations into popular products (Notion, Slack, VS Code, etc.)
- Research announcements that lead to usable tools or features
- AI agent frameworks and platforms

## WHAT IS NOT RELEVANT (skip it):
- Hardware/chip announcements (GPUs, TPUs, custom silicon) unless they directly enable a new software tool
- Corporate earnings, funding rounds, valuations, hiring, layoffs
- General "how to use ChatGPT" tutorials/guides (we want NEWS, not tutorials)
- Opinion pieces, predictions, "state of AI" essays without new announcements
- Government regulation/policy news (unless it directly affects tool availability)
- Academic papers with no practical application or tool release
- Vague "AI will change everything" articles with no specific news

## OUTPUT FORMAT (strict JSON)
{
  "article": "the article text (preserved exactly as received)",
  "is_relevant": true/false,
  "reason": "1-2 sentence explanation of why it's relevant or not"
}

## RULES
- When in doubt, lean toward RELEVANT (better to show more than miss important news)
- Focus on: can AIF readers DO something with this? (use a tool, try an API, build with a framework)
- Output ONLY valid JSON, nothing else"""

# ── Implementation ────────────────────────────────────────────
from utils.openrouter_client import chat_completion
from utils.logger import log_info
from utils.telegram_error import send_error


def execute(article: dict) -> dict | None:
    """
    Check if an article is relevant for the AI news channel.

    Args:
        article: {article_text, article_title, article_url, ...}

    Returns:
        Article with 'relevance_reason' added, or None if not relevant.
    """
    try:
        prompt = PROMPT.format(article_text=article["article_text"])

        result = chat_completion(
            prompt=prompt,
            system_message=SYSTEM_MESSAGE,
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=True,
        )

        is_relevant = result.get("is_relevant", False)
        reason = result.get("reason", "No reason provided")

        if not is_relevant:
            log_info(f"[Relevance] ✗ Not relevant: {article.get('article_title', 'Unknown')} — {reason}")
            return None

        article["relevance_reason"] = reason
        log_info(f"[Relevance] ✓ Relevant: {article.get('article_title', 'Unknown')}")
        return article

    except Exception as e:
        log_info(f"[Relevance] Error: {e}")
        send_error(str(e), node_name="relevance_checker")
        return None


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    # Test with AI tool article (should be relevant)
    test = {
        "article_text": "OpenAI released a new SDK that lets developers embed GPT-4 into their apps with just 3 lines of code. The SDK supports streaming, function calling, and structured outputs.",
        "article_title": "OpenAI Releases New SDK",
        "article_url": "https://example.com/test",
    }
    result = execute(test)
    print("RELEVANT" if result else "NOT RELEVANT")
