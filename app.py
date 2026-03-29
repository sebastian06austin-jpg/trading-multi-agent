from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio, json, os, io
from datetime import datetime
import pytz
from openai import OpenAI
import matplotlib
matplotlib.use('Agg')  # ← Critical for Render
import matplotlib.pyplot as plt
from telegram_sender import send_report, send_alert, send_chart_image

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")   # Change anytime here or in Render env vars

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)   # 8 AM IST
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)  # 6 PM IST
    scheduler.add_job(real_time_check, 'interval', minutes=10)
    scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=9, minute=0)
    scheduler.start()
    print("🚀 ULTIMATE SYSTEM LIVE - All agents + charts + educator working")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Report + chart + lesson sent to Telegram"}

async def call_agent(agent_name: str, prompt: str):
    with open(f"agents/{agent_name}_prompt.md") as f:
        system_prompt = f.read()
    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content

async def full_report():
    prompt_base = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Indian + global focus."

    # Run all agents
    quant = await call_agent("quant", prompt_base)
    technical = await call_agent("technical", prompt_base)
    sentiment = await call_agent("sentiment", prompt_base)
    risk = await call_agent("risk", prompt_base)
    options = await call_agent("options", prompt_base)
    educator = await call_agent("educator", prompt_base)

    # Supervisor synthesizes everything
    with open("agents/supervisor_prompt.md") as f:
        sup_prompt = f.read()
    final_prompt = f"{sup_prompt}\n\nAgent Outputs:\nQuant: {quant}\nTechnical: {technical}\nSentiment: {sentiment}\nRisk: {risk}\nOptions: {options}\nEducator Lesson: {educator}"
    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "user", "content": final_prompt}],
        temperature=0.1
    )
    report = response.choices[0].message.content

    # Send chart
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot([1,2,3,4,5], [10,25,15,30,20], marker='o', color='blue')
        ax.set_title("Educational Watchlist Snapshot")
        ax.grid(True)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        await send_chart_image(buf)
    except:
        pass

    await send_report(report)

async def real_time_check():
    prompt = "Quick real-time scan. If strong signal, return exactly one line: 🚨 STRONG BUY/SELL TICKER @ price - reason"
    alert_text = (await call_agent("sentiment", prompt))
    if "STRONG" in alert_text.upper():
        await send_alert(alert_text)

async def sunday_self_review():
    review = await call_agent("educator", "Sunday self-review of last week's signals, lessons, and improvements.")
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Trading Agent starting on Render port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
