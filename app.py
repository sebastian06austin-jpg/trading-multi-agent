from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio, json, os
from datetime import datetime
import pytz
from graph import app as langgraph_app  # we'll create graph.py same as before
from telegram_sender import send_report, send_alert
from tools.custom_tools import get_nse_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    
    # Full reports at 8 AM & 6 PM IST
    scheduler.add_job(full_report_job, 'cron', hour=2, minute=30)
    scheduler.add_job(full_report_job, 'cron', hour=12, minute=30)
    
    # REAL-TIME alerts every 10 min during market hours
    scheduler.add_job(real_time_alert_check, 'interval', minutes=10)
    
    scheduler.start()
    print("🚀 24/7 Multi-Agent System started on Render")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "alive", "time": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()}

async def full_report_job():
    await run_full_analysis("full_report")

async def real_time_alert_check():
    await run_full_analysis("alert_check")

async def run_full_analysis(mode: str):
    with open("portfolio.json") as f:
        port = json.load(f)
    
    watchlist = ["^NSEI", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]
    data = {t: get_nse_data.invoke({"ticker": t}) for t in watchlist}
    
    input_text = f"Mode: {mode} | Time: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')} | Data: {data} | Capital: ₹{port['capital']}"
    
    result = langgraph_app.invoke({"messages": [input_text], "portfolio": port})
    report = result["messages"][-1]
    
    await send_report(report)
    
    if "STRONG BUY" in report or "STRONG SELL" in report:
        await send_alert("🚨 HIGH-CONFIDENCE SIGNAL DETECTED!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
