import os
from telegram import Bot
import asyncio

async def send_report(md: str):
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    await bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text=md, parse_mode="MarkdownV2")

def send_alert(text: str):
    asyncio.run(send_report(f"🚨 {text}"))
