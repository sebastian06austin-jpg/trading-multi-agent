from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio, os
from database import get_user_prefs, set_user_pref, save_message, get_user_history
from dhan_tools import get_dhan_live_quote, get_dhan_portfolio  # import your MCP or direct calls

app = FastAPI()

# Telegram conversational bot
application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text.lower()
    save_message(user_id, "user", user_text)

    prefs = get_user_prefs(user_id)

    # Auto-detect preference updates
    if "set my risk" in user_text:
        risk = "low" if "low" in user_text else "high" if "high" in user_text else "medium"
        set_user_pref(user_id, "risk_level", risk)
        await update.message.reply_text(f"✅ Risk level updated to **{risk}**")
        return

    if "favorite" in user_text or "add to favorites":
        # simple parsing
        set_user_pref(user_id, "favorites", ["RELIANCE", "TCS"])  # example
        await update.message.reply_text("✅ Favorites updated")
        return

    # Normal Grok-like chat
    history = get_user_history(user_id)
    system_prompt = f"You are Grok. User preferences: risk={prefs['risk_level']}, favorites={prefs['favorites']}. Be helpful, trading-focused."

    response = client.chat.completions.create(
        model=os.getenv("GROK_MODEL", "grok-4.20-reasoning"),
        messages=[{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_text}],
        temperature=0.7
    )
    reply = response.choices[0].message.content
    save_message(user_id, "assistant", reply)
    await update.message.reply_text(reply)

# Add handlers
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

# Run bot in background
async def run_bot():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
