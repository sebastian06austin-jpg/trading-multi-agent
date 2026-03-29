from fastapi import FastAPI
from contextlib import asynccontextmanager
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
    print("🚀 ULTIMATE SYSTEM STARTED SUCCESSFULLY ON RENDER")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Ultimate report + chart + lesson sent to Telegram"}

async def full_report():
    base_prompt = f"""
    You are the Ultimate Multi-Agent Trading System (Chief Strategist + Quant + Technical + Sentiment + Risk + Options + Educator Agent).
    Time: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}
    Focus: Indian market (NSE) + global. Small/mid/large cap. Use Dhan app for execution.

    Structure the report EXACTLY like this:

    **DISCLAIMER**: Educational paper-trading simulation only. Not financial advice. Use at your own risk in Dhan app.

    **STOCKS** (Indian + global)
    - Company name + key info
    - Method & indicators to use
    - When to buy/sell/hold (long/short)
    - Quantity & capital allocation (max 1-2% risk)
    - TradingView link + Dhan note

    **COMMODITIES**

    **ETFs**

    **CRYPTO**

    **EDUCATOR LESSON** (long, powerful, detailed teaching on market, psychology, risk, indicators, Dhan usage, etc.)

    **Sunday Self-Review** (if today is Sunday)

    End with Confidence: X/10
    """

    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "user", "content": base_prompt}],
        temperature=0.1
    )
    report = response.choices[0].message.content

    # Send chart
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting ultimate system on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
