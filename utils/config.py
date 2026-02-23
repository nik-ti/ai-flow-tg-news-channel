"""
UTIL: Configuration
PURPOSE: Centralized config loader from .env — single source of truth for all API keys,
         channel IDs, model names, and microservice URLs.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Get required env var or raise."""
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val


# ── Telegram ────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
ADMIN_CHANNEL_ID = _require("ADMIN_CHANNEL_ID")
MAIN_CHANNEL_ID = os.getenv("MAIN_CHANNEL_ID", "@aiflowdaily")
RU_CHANNEL_ID = os.getenv("RU_CHANNEL_ID", "@aiflowdaily_ru")

# ── AI Models (all via OpenRouter) ──────────────────────────
OPENROUTER_API_KEY = _require("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Notion ──────────────────────────────────────────────────
NOTION_TOKEN = _require("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "2a90bc015b5e80cb9385f64b6e7052c1")

# ── Microservices ───────────────────────────────────────────
AI_PARSER_URL = os.getenv("AI_PARSER_URL", "https://parser.simple-flow.co/parse")
IMAGE_FINDER_URL = os.getenv("IMAGE_FINDER_URL", "https://find-image.simple-flow.co")

# ── Tavily ──────────────────────────────────────────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── Scheduling ──────────────────────────────────────────────
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "10"))

# ── RSS Feed URLs ───────────────────────────────────────────
RSS_FEEDS = {
    "marktechpost": "https://www.marktechpost.com/feed/",
    "techcrunch": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "theverge": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
}

# ── Website sources (parsed via AI parser) ──────────────────
WEBSITE_SOURCES = {
    "aibase": "https://news.aibase.com/news",
    "futuretools": "https://www.futuretools.io/news",
    "gemini": "https://blog.google/products-and-platforms/products/gemini/",
}

# ── Channel signature ──────────────────────────────────────
EN_SIGNATURE = '\n\n<a href="https://t.me/aiflowdaily"><b>AI Flow Daily</b></a>'
RU_SIGNATURE = '\n\n<a href="https://t.me/aiflowdaily_ru"><b>AI Flow Daily</b></a>'
