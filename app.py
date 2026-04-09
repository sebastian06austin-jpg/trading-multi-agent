from fastapi import FastAPI
import asyncio, os, io
from datetime import datetime
import pytz
from openai import OpenAI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram_sender import send_report, send_alert, send_chart_image
from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio, os
from database import get_user_prefs, set_user_pref, save_message, get_user_history
from dhan_tools import get_dhan_live_quote, get_dhan_portfolio  # import your MCP or direct calls

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Ultimate report + chart sent to Telegram"}

async def full_report():
    prompt = f"""Create the ultimate trading report for {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}.

**DISCLAIMER:** This is educational paper-trading only. Not financial advice. Use in Dhan at your own risk. Past performance is not guarantee of future results.

**STOCKS** (Indian + Global, small/mid/large cap)
- Company name + key info
- Best method & indicators to use
- When to buy/sell/hold (long/short)
- Suggested quantity & capital allocation (max 1-2% risk)
- TradingView link + Dhan note

**COMMODITIES**
**ETFs**
**CRYPTO**

**EDUCATOR LESSON** (long, detailed, powerful teaching about trading, market psychology, risk management, Dhan app usage, indicators, etc.)

Be specific, actionable, and educational."""

    try:
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        report = response.choices[0].message.content
    except Exception as e:
        report = f"Error calling Grok: {str(e)}"

    # Chart
    try:
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot([1,2,3,4,5], [10,25,15,30,20], marker='o', color='blue')
        ax.set_title("Educational Market Snapshot")
        ax.grid(True)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        await send_chart_image(buf)
    except:
        pass

    await send_report(report)

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
    print(f"🚀 Ultimate system starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
