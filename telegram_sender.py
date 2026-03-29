import os
from telegram import Bot
import asyncio

async def send_report(md: str):
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    MAX = 4000
    if len(md) <= MAX:
        await bot.send_message(chat_id=chat_id, text=md)
        return
    # split logic (same as before)
    parts = []
    while md:
        if len(md) <= MAX:
            parts.append(md)
            break
        split_at = md.rfind('\n', 0, MAX)
        if split_at == -1: split_at = MAX
        parts.append(md[:split_at])
        md = md[split_at:].lstrip('\n')
    for i, part in enumerate(parts, 1):
        await bot.send_message(chat_id=chat_id, text=f"📊 Report Part {i}/{len(parts)}\n\n{part}")

async def send_alert(text: str):
    await send_report(f"🚨 {text}")

async def send_chart_image(buf: io.BytesIO):
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    buf.seek(0)
    await bot.send_photo(chat_id=os.getenv("TELEGRAM_CHAT_ID"), photo=buf, caption="📈 Watchlist Chart")
