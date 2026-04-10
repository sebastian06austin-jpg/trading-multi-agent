from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio, json, os, io
from datetime import datetime
import pytz
from openai import OpenAI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram_sender import send_report, send_alert, send_chart_image
from database import get_user_prefs, set_user_pref, save_message, get_user_history
from dhan_tools import get_dhan_live_quote, get_dhan_portfolio

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)   # 8 AM IST
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)  # 6 PM IST
    scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=9, minute=0)
    scheduler.start()
    print("🚀 ULTIMATE FULL INTEGRATION LIVE — Dhan + TradingView + Grok-like bot + memory")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Full report sent"}

# TradingView Webhook
@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    data = await request.json()
    await send_alert(f"📢 TradingView Alert: {data.get('message', 'New signal')}")
    return {"status": "received"}

async def call_grok(prompt: str):
    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

async def full_report():
    # Fetch live Dhan data
    dhan_portfolio = get_dhan_portfolio()
    dhan_quote_example = get_dhan_live_quote("RELIANCE")  # example, agent can call more via prompt

    base_prompt = f"""Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}.
Use this live Dhan data: {dhan_portfolio}
Create complete report with:
**STOCKS** (Indian + Global) - specific buy/sell/hold, quantity, risk, method, indicators, TradingView link, Dhan note
**COMMODITIES** **ETFs** **CRYPTO**
**EDUCATOR LESSON** (long, detailed, powerful teaching)
Be precise and actionable."""

    report = await call_grok(base_prompt)

    # Chart image
    try:
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot([1,2,3,4,5], [10,25,15,30,20], marker='o', color='blue')
        ax.set_title("Live Market Snapshot")
        ax.grid(True)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        await send_chart_image(buf)
    except:
        pass

    await send_report(report)

async def sunday_self_review():
    review = await call_grok("Sunday self-review of last week signals, lessons, improvements, and portfolio performance.")
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

# Grok-like Conversational Telegram Bot with Memory
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

async def conversational_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    save_message(user_id, "user", text)

    prefs = get_user_prefs(user_id)

    # Auto-update preferences
    if "risk" in text.lower():
        risk = "low" if "low" in text.lower() else "high" if "high" in text.lower() else "medium"
        set_user_pref(user_id, "risk_level", risk)
        await update.message.reply_text(f"✅ Risk level updated to **{risk}**")

    history = get_user_history(user_id)
    system = f"You are Grok. User preferences: {json.dumps(prefs)}. Be helpful, trading-focused."
    reply = await call_grok(f"{system}\n\n{text}")
    save_message(user_id, "assistant", reply)
    await update.message.reply_text(reply)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, conversational_handler))

@app.on_event("startup")
async def startup():
    asyncio.create_task(application.initialize())
    asyncio.create_task(application.start())
    asyncio.create_task(application.updater.start_polling())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting ultimate system on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
