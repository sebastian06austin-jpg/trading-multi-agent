import os
from telegram import Bot

async def send_report(md: str):
    """Send full report to Telegram (Markdown format)"""
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    await bot.send_message(
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        text=md,
        parse_mode="Markdown"   # Simple Markdown — no more # errors
    )

async def send_alert(text: str):
    """Send quick alert (used for real-time strong signals)"""
    await send_report(f"🚨 {text}")
