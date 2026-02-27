"""
AI Flow Daily — Main Orchestrator
==================================
Runs two parallel components:
  1. APScheduler: triggers article pipeline every 10 min
  2. Telegram Bot: listens for admin approval callbacks

Pipeline per article:
  fetch → summarize → relevance → dedup → write → fix_html
  → find_creative → save_to_notion → admin_preview
  → [on approve] post_to_main → update_notion → translate → post_to_ru
  → [on decline] update_notion
"""

import asyncio
import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.config import TELEGRAM_BOT_TOKEN, POLL_INTERVAL_MINUTES
from utils.logger import log_info, log_error, get_logger, log_section
from utils.telegram_error import send_error
from utils import notion_client

# Node imports
from nodes import fetch_rss, fetch_websites
from nodes import summarizer, relevance_checker, duplicate_control
from nodes import post_writer, fix_html, find_creative
from nodes import save_to_notion, post_to_telegram
from nodes import translator, translation_reviewer, post_to_ru


# ── Pipeline ─────────────────────────────────────────────────


async def process_article(article: dict, bot) -> None:
    """Run the full AI pipeline for a single article.
    
    All synchronous node calls (OpenRouter, Notion, HTTP) are wrapped in
    asyncio.to_thread() so they run in background threads and never block
    the Telegram polling loop. This keeps buttons responsive at all times.
    """

    source = article.get("source", "unknown")
    url = article.get("article_url", "unknown")
    log_section(f"Processing [{source}]: {url}")

    # 1. Summarize (sync OpenRouter call → thread)
    article = await asyncio.to_thread(summarizer.execute, article)
    if not article:
        log_info("  ↳ Skipped by Summarizer")
        return

    # 2. Relevance check (sync OpenRouter call → thread)
    article = await asyncio.to_thread(relevance_checker.execute, article)
    if not article:
        log_info("  ↳ Skipped by Relevance Checker")
        return

    # 3. Duplicate control (sync OpenRouter call → thread)
    article = await asyncio.to_thread(duplicate_control.execute, article)
    if not article:
        log_info("  ↳ Skipped by Duplicate Control")
        return

    # 4. Write post (sync OpenRouter call → thread)
    post_text = await asyncio.to_thread(post_writer.execute, article)
    if not post_text:
        log_info("  ↳ Skipped by Post Writer (empty output)")
        return

    # 5. Fix HTML + add signature (fast, but thread for safety)
    post_text = await asyncio.to_thread(fix_html.execute, post_text)

    # 6. Find creative (sync HTTP call → thread)
    creative = await asyncio.to_thread(find_creative.execute, article)

    # 7. Build article data for approval flow
    article_data = {
        "post_text": post_text,
        "creative_type": creative["creative_type"],
        "creative_url": creative["creative_url"],
        "article_title": article.get("article_title", ""),
        "article_url": article.get("article_url", ""),
        "relevance_reason": article.get("relevance_reason", ""),
    }

    # 8. Save to Notion (sync Notion call → thread)
    page_id = await asyncio.to_thread(
        save_to_notion.create_row,
        title=article.get("article_title", ""),
        article_url=article.get("article_url", ""),
        creative_url=creative["creative_url"],
        post_text=post_text,
        why_relevant=article.get("relevance_reason", ""),
    )
    article_data["notion_page_id"] = page_id

    # 9. Send preview to admin channel (already async)
    callback_id = await post_to_telegram.send_preview(bot, article_data)
    if not callback_id:
        log_error("  ↳ Failed to send admin preview")
        return

    log_info(f"  ↳ Awaiting approval (callback:{callback_id})")


async def run_pipeline(bot) -> None:
    """Fetch all sources and process new articles."""
    log_section("Pipeline started")

    try:
        # Fetch from all sources (sync HTTP/RSS calls → threads)
        articles = []
        rss_articles = await asyncio.to_thread(fetch_rss.execute)
        articles.extend(rss_articles)
        web_articles = await asyncio.to_thread(fetch_websites.execute)
        articles.extend(web_articles)

        if not articles:
            log_info("No new articles found")
            log_section("Pipeline finished")
            return

        log_info(f"Found {len(articles)} new article(s) to process")

        # Process each article
        for article in articles:
            try:
                await process_article(article, bot)
            except Exception as e:
                log_error(f"Error processing article {article.get('article_url')}: {e}")
                send_error(str(e), node_name="main_pipeline")

    except Exception as e:
        log_error(f"Pipeline error: {e}")
        send_error(str(e), node_name="main_pipeline")

    log_section("Pipeline finished")


# ── Approval Callback Handler ────────────────────────────────


async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Approve/Decline button presses from admin channel."""
    query = update.callback_query
    await query.answer()  # Acknowledge immediately

    data = query.data  # "approve:UUID" or "decline:UUID"
    parts = data.split(":", 1)
    if len(parts) != 2:
        return

    action, page_id = parts

    try:
        # 1. Try to get data from memory first
        article_data = post_to_telegram.pending_posts.get(page_id)

        # 2. Fallback: Fetch from Notion if not in memory (stateless)
        bot = context.bot
        if not article_data:
            log_info(f"Callback data not in memory, fetching Notion page: {page_id}")
            article_data = await asyncio.to_thread(notion_client.get_article_data, page_id)

            if not article_data:
                await query.edit_message_text(f"⚠️ Error: Post data not found in Notion ({page_id})")
                return

            # Infer creative type since we don't store it explicitly in Notion properties
            c_url = article_data.get("creative_url", "")
            if c_url and c_url.lower().endswith((".mp4", ".mov", ".webm")):
                article_data["creative_type"] = "video"
            elif c_url and c_url != "none":
                article_data["creative_type"] = "image"
            else:
                article_data["creative_type"] = "none"
            
            # Check status to prevent double-posting
            status = article_data.get("status")
            if status == "Posted":
                await query.edit_message_text(f"✅ Already Posted: {article_data.get('title')}")
                return
            elif status == "Declined":
                await query.edit_message_text(f"❌ Already Declined: {article_data.get('title')}")
                return

        # 3. Handle Actions
        title_to_show = article_data.get("article_title", article_data.get("title", "Unknown"))
        if action == "approve":
            log_info(f"Processing approval for {page_id}")
            
            result = await post_to_telegram.post_to_main_channel(bot, article_data)

            if result:
                # Update Notion: Posted
                await asyncio.to_thread(save_to_notion.mark_posted, page_id, result["post_url"])

                # Remove from pending if it was there
                if page_id in post_to_telegram.pending_posts:
                     del post_to_telegram.pending_posts[page_id]

                # Edit admin message
                await query.edit_message_text(f"✅ Approved & Posted: {title_to_show}")

                # Trigger RU translation workflow
                asyncio.create_task(_run_ru_pipeline(bot, article_data))

            else:
                await query.edit_message_text(f"⚠️ Error posting to main channel.")

        elif action == "decline":
            log_info(f"Declining post {page_id}")
            
            # Update Notion: Declined
            await asyncio.to_thread(save_to_notion.mark_declined, page_id)
            
            # Remove from pending if it was there
            if page_id in post_to_telegram.pending_posts:
                 del post_to_telegram.pending_posts[page_id]

            await query.edit_message_text(f"❌ Declined: {title_to_show}")

    except Exception as e:
        log_error(f"[Approval] Unhandled error: {e}")
        send_error(f"Approval handler crashed: {e}", node_name="handle_approval")
        try:
            await query.edit_message_text(f"⚠️ Error processing action: {str(e)[:200]}")
        except Exception:
            pass


async def _run_ru_pipeline(bot, article_data: dict) -> None:
    """Run the Russian translation and posting pipeline."""
    try:
        en_text = article_data["post_text"]

        # 1. Translate to Russian (sync call → run in thread)
        ru_text = await asyncio.to_thread(translator.execute, en_text)
        if not ru_text:
            log_error("[RU Pipeline] Translation failed, skipping RU post")
            return

        # 2. Quality review (sync call → run in thread)
        ru_text = await asyncio.to_thread(translation_reviewer.execute, ru_text)

        # 3. Post to Russian channel
        await post_to_ru.execute(
            bot=bot,
            ru_post_text=ru_text,
            creative_type=article_data.get("creative_type", "none"),
            creative_url=article_data.get("creative_url", "none"),
        )

    except Exception as e:
        log_error(f"[RU Pipeline] Error: {e}")
        send_error(str(e), node_name="ru_pipeline")


# ── Main Entry Point ─────────────────────────────────────────


def main():
    """Start the bot and scheduler."""
    log_info("🚀 AI Flow Daily starting...")

    # Build Telegram application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register callback handler for approval buttons
    app.add_handler(CallbackQueryHandler(handle_approval))

    # Set up scheduler
    scheduler = AsyncIOScheduler()

    async def scheduled_job():
        """Run pipeline using the bot's instance."""
        await run_pipeline(app.bot)

    scheduler.add_job(
        scheduled_job,
        "interval",
        minutes=POLL_INTERVAL_MINUTES,
        next_run_time=datetime.now(timezone.utc),  # Run immediately on start
        id="article_pipeline",
        name="Article Pipeline",
    )

    # Start scheduler when app starts
    async def post_init(application: Application):
        scheduler.start()
        log_info(f"⏰ Scheduler started (every {POLL_INTERVAL_MINUTES} min)")

    app.post_init = post_init

    # Run bot (blocks forever)
    log_info("🤖 Bot is listening for approvals...")
    app.run_polling(allowed_updates=[Update.CALLBACK_QUERY])


if __name__ == "__main__":
    main()
