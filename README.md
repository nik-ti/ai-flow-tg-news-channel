# AI Flow Daily — Python Automation

Automated AI news pipeline for Telegram channels [@aiflowdaily](https://t.me/aiflowdaily) (EN) and [@aiflowdaily_ru](https://t.me/aiflowdaily_ru) (RU).

## Overview

Monitors 5 AI news sources every 10 minutes, processes articles through an AI pipeline (summarize → relevance → dedup → write → creative), sends to admin for approval, then posts to Telegram, translates to Russian, and tracks everything in Notion.

## Features

- **Stateless Approval Flow:** Admin approval buttons work even after restarting the script. Data is automatically recovered from Notion if not found in memory.
- **Resilient Parsing:** Automatic fallback to Tavily if the AI parser microservice fails.
- **Robust Alerts:** Telegram notifications for both logic errors (`ok: false`) and crashes/502s.
- **Cleaner Logs:** Concise, colorized console output with visual separators.

## Flow Map

```
┌──────────── SOURCES ────────────┐
│ RSS:  marktechpost, techcrunch, │
│       theverge                  │
│ Web:  aibase.com, futuretools   │
└─────────────┬───────────────────┘
              ▼
   ┌──── AI PIPELINE ────┐
   │ 1. Summarizer       │  ← Gemini 2.5 Flash
   │ 2. Relevance Check  │  ← GPT-4.1 mini
   │ 3. Duplicate Control│  ← Gemini 2.5 Flash
   │ 4. Post Writer      │  ← Claude Sonnet 4.5
   │ 5. Fix HTML         │
   └──────────┬──────────┘
              ▼
   ┌──── CREATIVE ───────┐
   │ Video check → Image │  ← image-finder microservice
   │ finder → text-only  │
   └──────────┬──────────┘
              ▼
   ┌──── APPROVAL ───────┐
   │ Save to Notion      │
   │ Preview → Admin     │  ← Inline Approve/Decline buttons
   └────┬─────────┬──────┘
        │         │
    Approve    Decline
        │         │
        ▼         ▼
   Post to     Mark as
   @aiflowdaily  Declined
        │       in Notion
        ▼
   ┌──── RU PIPELINE ───┐
   │ 1. Translator      │  ← Claude Sonnet 4.5
   │ 2. Quality Review  │  ← Claude Sonnet 4.5
   │ 3. Post to RU      │
   └────────────────────┘
```

## Node Breakdown

| Node | File | Model | Purpose |
|------|------|-------|---------|
| Fetch RSS | `nodes/fetch_rss.py` | — | RSS feeds via feedparser + AI Parser |
| Fetch Websites | `nodes/fetch_websites.py` | — | AI Parser list→detail + Tavily fallback |
| Summarizer | `nodes/summarizer.py` | Gemini 2.5 Flash | Extract main point, ≤1500 chars |
| Relevance Checker | `nodes/relevance_checker.py` | GPT-4.1 mini | Filter non-AI-tool news |
| Duplicate Control | `nodes/duplicate_control.py` | Gemini 2.5 Flash | URL + AI semantic dedup |
| Post Writer | `nodes/post_writer.py` | Claude Sonnet 4.5 | Write 300-550 char Telegram post |
| Fix HTML | `nodes/fix_html.py` | — | Clean HTML + append signature |
| Find Creative | `nodes/find_creative.py` | — | Video/image via image-finder |
| Save to Notion | `nodes/save_to_notion.py` | — | Create/update Notion rows |
| Post to Telegram | `nodes/post_to_telegram.py` | — | Admin approval + main channel |
| Translator | `nodes/translator.py` | Claude Sonnet 4.5 | EN→RU rewrite |
| Translation Reviewer | `nodes/translation_reviewer.py` | Claude Sonnet 4.5 | Quality double-check |
| Post to RU | `nodes/post_to_ru.py` | — | Post to @aiflowdaily_ru |

## Architecture

### Process Structure

One Python process (`main.py`) runs two components on the same async event loop:

1. **Telegram Bot** (`python-telegram-bot` + `run_polling`) — Listens for Approve/Decline button presses 24/7.
2. **Scheduler** (`APScheduler`) — Fires the article pipeline every 10 minutes.

### Threading Rules

All synchronous calls (OpenRouter, Notion, image downloads, RSS fetching) **must** be wrapped in `asyncio.to_thread()` inside `main.py`. This applies to every node's `.execute()` function and any `requests`-based HTTP call. Telegram bot calls (`bot.send_message`, etc.) are already async and do not need wrapping.

```python
# Synchronous node call — always wrap:
article = await asyncio.to_thread(summarizer.execute, article)

# Async Telegram call — use directly:
await bot.send_message(chat_id=CHANNEL_ID, text=post_text)
```

### Node Convention

Each node in `nodes/` follows the same pattern:
- **`execute()`** — synchronous function, takes input dict, returns output dict or `None` to skip.
- Nodes are stateless — no shared state between calls.
- AI nodes use `utils/openrouter_client.py` for all LLM calls.
- Each node has a standalone `if __name__ == "__main__"` test block.

### Error Handling

- Pipeline errors are caught per-article, logged, and sent to admin's Telegram DM (`ADMIN_USER_ID`).
- The approval handler is wrapped in `try/except` — any crash sends error details to admin DM and updates the admin channel message.
- Error alerts use `utils/telegram_error.py` → `send_error(message, node_name)`.

## Setup

1. Copy `.env.example` to `.env` and fill in all values
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   python main.py
   ```

## Docker

```bash
docker compose up -d
```

## Debugging

- **Logs:** `automation.log` (file) + console output
- **Errors:** All errors sent directly to admin's Telegram DM
- **Standalone test:** Each node has `if __name__ == "__main__"` test block
  ```bash
  python -m nodes.summarizer
  python -m nodes.relevance_checker
  ```
