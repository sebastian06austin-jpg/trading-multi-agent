from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio, json, os
from datetime import datetime
import pytz
from openai import OpenAI
from telegram_sender import send_report, send_alert

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
MCP_URL = os.getenv("MCP_URL")  # Set in Render env vars

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)   # 8 AM IST
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)  # 6 PM IST
    scheduler.add_job(real_time_check, 'interval', minutes=10)
    scheduler.start()
    print("🚀 24/7 MCP Multi-Agent System LIVE")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health(): 
    return {"status": "alive", "time": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()}

async def call_grok(prompt: str):
    with open("agents/supervisor_prompt.md") as f:
        system_prompt = f.read()
    
    response = client.chat.completions.create(
        model="grok-4-1-fast-non-reasoning",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content

async def full_report():
    prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Use MCP tools for data/portfolio."
    report = await call_grok(prompt)
    await send_report(report)

async def real_time_check():
    prompt = f"""
    Quick real-time scan at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}.
    If there is ANY strong buy/sell signal on Nifty, any stock, or IPO grey-market buzz:
        Return ONLY ONE short line like this:
        🚨 STRONG BUY RELIANCE.NS @ ₹2850 - Reason: breakout above resistance + high volume
    If no strong signal, return exactly: NO SIGNAL
    """
    alert_text = await call_grok(prompt)
    
    if "STRONG" in alert_text.upper() and "NO SIGNAL" not in alert_text.upper():
        await send_alert(alert_text)   # Now it shows stock, price, reason!

@app.get("/trigger-report")
async def trigger_report():
    try:
        print("🚀 Manual report triggered at", datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST"))
        await full_report()          # This runs the full Grok + MCP + Telegram
        return {"status": "✅ SUCCESS! Full report sent to your Telegram. Check now!"}
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print("❌ ERROR:", error_msg)
        return {"status": "❌ Error occurred", "detail": str(e), "traceback": error_msg}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
