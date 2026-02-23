"""
NODE: Translation Reviewer
PURPOSE: Quality double-check of Russian translation for naturalness and idiomacy.
         Fixes awkward phrasings while preserving meaning, HTML tags, and emojis.
INPUT: Russian post text (HTML) from translator
OUTPUT: Polished Russian post text (HTML) or original if already good
"""

# ── AI Configuration ─────────────────────────────────────────
MODEL = "anthropic/claude-sonnet-4.5"
TEMPERATURE = 0.5
MAX_TOKENS = 1500

PROMPT = "Post text: {post_text}"

SYSTEM_MESSAGE = """You are a Russian copywriting editor. You receive a Russian Telegram post and must review it for natural, native-quality Russian.

YOUR ONLY JOB:
Check if the wording sounds natural and native. Fix any awkward phrases or word choices that don't sound like something a native Russian speaker would write.

WHAT TO LOOK FOR:
- Unnatural word order or sentence structure
- Words that are technically correct but not idiomatic
- Phrases that sound translated rather than written in Russian
- Better synonym choices that sound more professional
- Grammar or style improvements

RULES YOU MUST FOLLOW:
1. Keep ALL HTML tags exactly as they are
2. Keep ALL emojis in the same positions
3. Keep the same overall length (around 700 characters max)
4. Keep the same meaning and key information
5. Only change words/phrases that need improvement - if nothing is wrong, dont change anything

If the text is already good, keep it as is and just output it. Only fix what needs fixing.

Your output must be a single JSON object:
{
  "post_text": "the corrected Russian text with all html tags and emojis preserved"
}

No explanations. No comments. Only valid JSON with the polished Russian text."""

# ── Implementation ────────────────────────────────────────────
from utils.openrouter_client import chat_completion
from utils.logger import log_info, log_error
from utils.telegram_error import send_error


def execute(ru_post_text: str) -> str:
    """
    Quality check and polish Russian translation.

    Args:
        ru_post_text: Russian post text (HTML) from translator

    Returns:
        Polished Russian text, or original on failure
    """
    try:
        result = chat_completion(
            prompt=PROMPT.format(post_text=ru_post_text),
            system_message=SYSTEM_MESSAGE,
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            json_mode=True,
        )

        polished = result.get("post_text", "")
        if not polished or len(polished.strip()) < 30:
            log_error("[Reviewer] Output too short, using original")
            return ru_post_text

        log_info(f"[Reviewer] ✓ Polished ({len(polished)} chars)")
        return polished

    except Exception as e:
        log_error(f"[Reviewer] Error (using original): {e}")
        send_error(str(e), node_name="translation_reviewer")
        return ru_post_text  # Fail-safe: return unpolished version


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    test_ru = '<b>GitHub открывает агентный рантайм Copilot как программируемый SDK 🤖</b>\n\nGitHub Copilot-SDK позволяет встроить тот же агентный цикл выполнения в ваши собственные приложения.\n\nДоступно для <b>Node.js, Python, Go и .NET</b> ⚡'
    result = execute(test_ru)
    print(f"\nPolished ({len(result)} chars):\n{result}")
