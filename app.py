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
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)
    scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=9, minute=0)
    scheduler.start()
    print("🚀 ULTIMATE SYSTEM LIVE — All features active")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Report sent"}

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
    dhan_data = get_dhan_portfolio()
    prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Use live Dhan data: {dhan_data}. Include all sections: Stocks, Commodities, ETFs, Crypto with precise recommendations + long Educator lesson."
    report = await call_grok(prompt)
    await send_report(report)

async def sunday_self_review():
    review = await call_grok("Sunday self-review")
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

# ====================== GROK-LIKE CONVERSATIONAL BOT ======================
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    save_message(user_id, "user", text)

    prefs = get_user_prefs(user_id)

    # Auto preference update
    if "risk" in text.lower():
        risk = "low" if "low" in text.lower() else "high" if "high" in text.lower() else "medium"
        set_user_pref(user_id, "risk_level", risk)
        await update.message.reply_text(f"✅ Risk level updated to **{risk}**")

    history = get_user_history(user_id)
    system = f"You are Grok. User preferences: {json.dumps(prefs)}. Be helpful, trading-focused, and fun."
    reply = await call_grok(f"{system}\n\n{text}")
    save_message(user_id, "assistant", reply)
    await update.message.reply_text(reply)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

@app.on_event("startup")
async def startup():
    asyncio.create_task(application.initialize())
    asyncio.create_task(application.start())
    asyncio.create_task(application.updater.start_polling())
    print("🚀 Telegram conversational bot started")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
