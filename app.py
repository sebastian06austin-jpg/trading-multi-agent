from fastapi import FastAPI
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

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        scheduler.add_job(full_report, 'cron', hour=2, minute=30)
        scheduler.add_job(full_report, 'cron', hour=12, minute=30)
        scheduler.add_job(real_time_check, 'interval', minutes=10)
        scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=9, minute=0)
        scheduler.start()
        print("🚀 ULTIMATE MULTI-AGENT SYSTEM STARTED SUCCESSFULLY")
    except Exception as e:
        print("Scheduler warning:", e)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Full ultimate report sent"}

async def call_agent(agent: str, prompt: str):
    with open(f"agents/{agent}_prompt.md") as f:
        system = f.read()
    resp = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.1
    )
    return resp.choices[0].message.content

async def full_report():
    base_prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Indian + global focus."

    quant = await call_agent("quant", base_prompt)
    technical = await call_agent("technical", base_prompt)
    sentiment = await call_agent("sentiment", base_prompt)
    risk = await call_agent("risk", base_prompt)
    options = await call_agent("options", base_prompt)
    educator = await call_agent("educator", base_prompt)

    with open("agents/supervisor_prompt.md") as f:
        sup = f.read()
    final_prompt = f"{sup}\n\nAgent Outputs:\nQuant: {quant}\nTechnical: {technical}\nSentiment: {sentiment}\nRisk: {risk}\nOptions: {options}\nEducator: {educator}"

    resp = client.chat.completions.create(model=GROK_MODEL, messages=[{"role": "user", "content": final_prompt}], temperature=0.1)
    report = resp.choices[0].message.content

    # Chart
    try:
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot([1,2,3,4,5], [10,25,15,30,20], marker='o')
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

async def real_time_check():
    alert = await call_agent("sentiment", "Quick scan. Return only one line if STRONG signal.")
    if "STRONG" in alert.upper():
        await send_alert(alert)

async def sunday_self_review():
    review = await call_agent("educator", "Sunday self-review of last week.")
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)from fastapi import FastAPI
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

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        scheduler.add_job(full_report, 'cron', hour=2, minute=30)
        scheduler.add_job(full_report, 'cron', hour=12, minute=30)
        scheduler.add_job(real_time_check, 'interval', minutes=10)
        scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=9, minute=0)
        scheduler.start()
        print("🚀 ULTIMATE MULTI-AGENT SYSTEM STARTED SUCCESSFULLY")
    except Exception as e:
        print("Scheduler warning:", e)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Full ultimate report sent"}

async def call_agent(agent: str, prompt: str):
    with open(f"agents/{agent}_prompt.md") as f:
        system = f.read()
    resp = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.1
    )
    return resp.choices[0].message.content

async def full_report():
    base_prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Indian + global focus."

    quant = await call_agent("quant", base_prompt)
    technical = await call_agent("technical", base_prompt)
    sentiment = await call_agent("sentiment", base_prompt)
    risk = await call_agent("risk", base_prompt)
    options = await call_agent("options", base_prompt)
    educator = await call_agent("educator", base_prompt)

    with open("agents/supervisor_prompt.md") as f:
        sup = f.read()
    final_prompt = f"{sup}\n\nAgent Outputs:\nQuant: {quant}\nTechnical: {technical}\nSentiment: {sentiment}\nRisk: {risk}\nOptions: {options}\nEducator: {educator}"

    resp = client.chat.completions.create(model=GROK_MODEL, messages=[{"role": "user", "content": final_prompt}], temperature=0.1)
    report = resp.choices[0].message.content

    # Chart
    try:
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot([1,2,3,4,5], [10,25,15,30,20], marker='o')
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

async def real_time_check():
    alert = await call_agent("sentiment", "Quick scan. Return only one line if STRONG signal.")
    if "STRONG" in alert.upper():
        await send_alert(alert)

async def sunday_self_review():
    review = await call_agent("educator", "Sunday self-review of last week.")
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
