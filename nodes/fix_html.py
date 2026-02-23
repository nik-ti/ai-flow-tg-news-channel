"""
NODE: Fix HTML
PURPOSE: Clean up HTML for Telegram's supported tags, normalize spacing,
         and append channel signature.
INPUT: Raw post text from post_writer
OUTPUT: Cleaned HTML string with channel signature
"""

import re
from utils.config import EN_SIGNATURE
from utils.logger import log_debug


def execute(post_text: str) -> str:
    """
    Clean HTML for Telegram compatibility and append signature.

    Args:
        post_text: Raw post text with HTML

    Returns:
        Cleaned and formatted post text
    """

    text = post_text

    # Replace <p> tags with double line breaks
    text = re.sub(r"<p>", "", text)
    text = re.sub(r"</p>", "\n\n", text)

    # Normalize <br> variants
    text = re.sub(r"<br\s*/?>", "\n", text)

    # Remove unsupported tags (keep: b, i, u, s, code, pre, a)
    # Strip any other HTML tags
    allowed_tags = {"b", "i", "u", "s", "code", "pre", "a"}
    def _strip_unsupported(match):
        tag = match.group(1).split()[0].strip("/").lower()
        if tag in allowed_tags:
            return match.group(0)
        return ""

    text = re.sub(r"<(/?\w[^>]*)>", _strip_unsupported, text)

    # Normalize consecutive blank lines (max 2 newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    # Append channel signature
    text += EN_SIGNATURE

    log_debug(f"[Fix HTML] Output: {len(text)} chars")
    return text


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    sample = '<b>Test headline 🚀</b>\n\n<p>Some paragraph with <b>bold</b> text.</p>\n<br><div>Unwanted div</div>\n\nFinal line here.'
    result = execute(sample)
    print(result)
