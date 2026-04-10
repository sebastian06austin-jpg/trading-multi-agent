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
from dhan_tools import get_dhan_live_quote, get_dhan_portfolio  # new

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)   # 8 AM IST
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)  # 6 PM IST
    scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=9, minute=0)
    scheduler.start()
    print("🚀 ULTIMATE UPGRADED SYSTEM LIVE")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Full upgraded report sent"}

# TradingView webhook
@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    data = await request.json()
    await send_alert(f"📢 TradingView Alert: {data.get('message', 'Signal')}")
    return {"status": "received"}

# Full Grok-like conversational bot (preserves old agent behavior)
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

async def conversational_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    save_message(user_id, "user", text)

    prefs = get_user_prefs(user_id)

    # Auto-update preferences from normal chat
    if "risk" in text.lower():
        risk = "low" if "low" in text.lower() else "high" if "high" in text.lower() else "medium"
        set_user_pref(user_id, "risk_level", risk)
        await update.message.reply_text(f"✅ Risk level updated to **{risk}**")

    # Normal Grok chat
    history = get_user_history(user_id)
    system = f"You are Grok. User prefs: {json.dumps(prefs)}. Be helpful, trading-focused."
    reply = await call_grok(text, [{"role": "system", "content": system}] + history)
    save_message(user_id, "assistant", reply)
    await update.message.reply_text(reply)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, conversational_handler))

async def call_grok(prompt: str, history=None):
    messages = history or []
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=GROK_MODEL, messages=messages, temperature=0.7)
    return resp.choices[0].message.content

async def full_report():
    # Old agent logic + new Dhan live data
    report = await call_grok("Full upgraded analysis using Dhan live data. Include all old sections + Educator lesson + TradingView links + Dhan notes.")
    await send_report(report)

async def sunday_self_review():
    review = await call_grok("Sunday self-review")
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

@app.on_event("startup")
async def startup():
    asyncio.create_task(application.initialize())
    asyncio.create_task(application.start())
    asyncio.create_task(application.updater.start_polling())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
