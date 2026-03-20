import os
from telegram import Bot

async def send_report(md: str):
    """Sends full report as plain text (no more parsing errors) + auto-splits if too long"""
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    MAX_LEN = 4000
    if len(md) <= MAX_LEN:
        await bot.send_message(chat_id=chat_id, text=md)  # ← NO parse_mode = safe
        return
    
    # Split safely
    parts = []
    while md:
        if len(md) <= MAX_LEN:
            parts.append(md)
            break
        split_at = md.rfind('\n', 0, MAX_LEN)
        if split_at == -1:
            split_at = MAX_LEN
        parts.append(md[:split_at])
        md = md[split_at:].lstrip('\n')
    
    for i, part in enumerate(parts, 1):
        prefix = f"📊 Trading Report — Part {i}/{len(parts)}\n\n"
        await bot.send_message(chat_id=chat_id, text=prefix + part)

async def send_alert(text: str):
    await send_report(f"🚨 {text}")
