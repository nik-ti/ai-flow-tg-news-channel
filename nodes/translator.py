"""
NODE: Translator
PURPOSE: Rewrites English post in natural Russian for @aiflowdaily_ru.
         Not a direct translation — writes as if originally composed in Russian.
INPUT: EN post text (HTML)
OUTPUT: RU post text (HTML) or None on failure
"""

# ── AI Configuration ─────────────────────────────────────────
MODEL = "anthropic/claude-sonnet-4.5"
TEMPERATURE = 0.7
MAX_TOKENS = 1500

PROMPT = "Post text: {post_text}"

SYSTEM_MESSAGE = """You are an expert Telegram post writer for Russian audiences. You will receive an English post and your job is to WRITE it in natural Russian, not translate it directly.

CRITICAL RULES:
1. Maximum 700 characters (including HTML tags, emojis, whitespace)
2. Write in natural, fluent Russian that sounds completely native - as if originally written by a Russian speaker
3. Retain all HTML tags exactly as in original (<b>, <i>, <u>, <s>, <code>, <pre>, <a href="">) - no new tags, no removed tags
4. Keep all emojis in the same positions
5. Maintain overall structure and all key points from the English version
6. Your goal is to REWRITE, not translate word-for-word
7. Dont forget to change hyperlink text as well (never the url itself)

YOUR WRITING APPROACH:
- You will receive an English post
- Read it to understand the core message and key facts
- WRITE the post fresh in Russian as if you're creating it from scratch
- Use natural Russian sentence structure, idioms, and expressions
- Choose words and phrases that native Russian speakers actually use in Telegram posts
- Avoid calques (word-for-word translations) that sound unnatural
- Don't invent new points or add information not in the original
- Keep the same tone: professional, engaging, clear

TONE & STYLE:
- Professional but conversational
- Clear and concise
- Engaging for Telegram audience
- Natural Russian phrasing, not "translated Russian"

TECHNICAL QUALITY:
- Grammar must be perfect for native speakers
- Word choice should feel natural, not borrowed from English
- Sentence flow should be smooth and idiomatic
- Technical terms should use correct Russian equivalents
- Punctuation and formatting should follow Russian conventions

HTML TAG USAGE:
- Use HTML tags throughout the post exactly as they appear in the English version
- Maintain the same emphasis and formatting structure
- Apply tags to the appropriate Russian words/phrases to preserve the original emphasis

OUTPUT FORMAT:
Return only a valid JSON object with no explanations, no comments, no additional text:
{
  "post_text": "your Russian post with all html tags and emojis preserved"
}

Remember: Your task is to WRITE in Russian, not translate into Russian. The result should read as if it was originally composed by a native Russian speaker for a Russian Telegram audience."""

# ── Implementation ────────────────────────────────────────────
from utils.openrouter_client import chat_completion
from utils.logger import log_info, log_error
from utils.telegram_error import send_error


def execute(en_post_text: str) -> str | None:
    """
    Rewrite English post in natural Russian.

    Args:
        en_post_text: English post text (HTML)

    Returns:
        Russian post text (HTML) or None on failure
    """
    try:
        result = chat_completion(
            prompt=PROMPT.format(post_text=en_post_text),
            system_message=SYSTEM_MESSAGE,
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=True,
        )

        ru_text = result.get("post_text", "")
        if not ru_text or len(ru_text.strip()) < 30:
            log_error(f"[Translator] Output too short: {len(ru_text)} chars")
            return None

        log_info(f"[Translator] ✓ {len(ru_text)} chars")
        return ru_text

    except Exception as e:
        log_error(f"[Translator] Error: {e}")
        send_error(str(e), node_name="translator")
        return None


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    test_en = '<b>GitHub opens up Copilot\'s agent runtime as a programmable SDK 🤖</b>\n\nThe GitHub Copilot-SDK lets you embed the same agentic execution loop into your own apps.\n\nAvailable in <b>Node.js, Python, Go, and .NET</b> ⚡'
    result = execute(test_en)
    if result:
        print(f"\nRU Post ({len(result)} chars):\n{result}")
