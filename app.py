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
from dhan_tools import get_dhan_live_quote, get_dhan_portfolio, get_trade_history

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)
    scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=9, minute=0)
    scheduler.start()
    print("🚀 FINAL ULTIMATE SYSTEM LIVE — Full Dhan + TradingView + Memory + Postback")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS!"}

# TradingView webhook
@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    data = await request.json()
    await send_alert(f"📢 TradingView Alert: {data.get('message', 'New signal')}")
    return {"status": "received"}

# Dhan Postback (real-time order updates)
@app.post("/dhan-postback")
async def dhan_postback(request: Request):
    try:
        data = await request.json()
        print("📨 Dhan Postback Received:", json.dumps(data, indent=2))
        
        status = data.get("orderStatus", "")
        symbol = data.get("tradingSymbol", "Unknown")
        
        if status in ["TRADED", "REJECTED", "CANCELLED", "PENDING"]:
            message = f"📨 Dhan Order Update\nSymbol: {symbol}\nStatus: {status}\nDetails: {json.dumps(data, default=str)}"
            await send_alert(message)
        return {"status": "received"}
    except Exception as e:
        print("Dhan postback error:", str(e))
        return {"status": "received"}

# Telegram Webhook (Grok-like chat)
@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
        if "message" not in update or "text" not in update["message"]:
            return {"status": "ok"}
        
        text = update["message"]["text"].strip().lower()
        user_id = str(update["message"]["from"]["id"])
        
        save_message(user_id, "user", text)
        prefs = get_user_prefs(user_id)

        # Special Dhan commands
        if text == "/portfolio" or "portfolio" in text or "holdings" in text or "positions" in text:
            data = get_dhan_portfolio()
            if "HOLDING_ERROR" in data or "No holdings available" in data:
                await send_alert("⚠️ Dhan returned HOLDING_ERROR (DH-1111).\nThis usually means the Access Token is in Sandbox mode or needs regeneration.\n\nPlease regenerate your token in **Live mode** and update env vars.")
            else:
                await send_alert(f"📊 **Your Live Dhan Portfolio & Positions:**\n{data}")
            return {"status": "ok"}

        if text == "/tradehistory" or "trade history" in text or "orders" in text or "history" in text:
            data = get_trade_history()
            if "Error" in data:
                await send_alert(f"📜 **Trade History:**\n{data}\n\nIf empty, regenerate token in Live mode.")
            else:
                await send_alert(f"📜 **Your Dhan Trade / Order History:**\n{data}")
            return {"status": "ok"}

        if text.startswith("/quote"):
            symbol = text.split()[-1].upper() if len(text.split()) > 1 else "RELIANCE"
            data = get_dhan_live_quote(symbol)
            await send_alert(f"📈 Live Quote for {symbol}:\n{data}")
            return {"status": "ok"}

        # Auto preference
        if "risk" in text:
            risk = "low" if "low" in text else "high" if "high" in text else "medium"
            set_user_pref(user_id, "risk_level", risk)
            await send_alert(f"✅ Risk level updated to **{risk}**")
            return {"status": "ok"}

        # Normal Grok chat with live Dhan data
        dhan_data = get_dhan_portfolio()
        history = get_user_history(user_id)
        system = f"You are Grok. You have full real-time access to the user's Dhan account. Current portfolio: {dhan_data}. User preferences: {json.dumps(prefs)}. Be helpful, trading-focused, and fun."
        reply = await call_grok(f"{system}\n\n{text}")
        save_message(user_id, "assistant", reply)
        await send_alert(reply)
        return {"status": "ok"}

    except Exception as e:
        print("Webhook error:", str(e))
        return {"status": "ok"}

async def call_grok(prompt: str):
    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

async def full_report():
    dhan_data = get_dhan_portfolio()
    prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Use live Dhan data: {dhan_data}. Include all sections with precise recommendations + long Educator lesson."
    report = await call_grok(prompt)
    await send_report(report)

async def sunday_self_review():
    review = await call_grok("Sunday self-review")
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
