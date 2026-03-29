from fastapi import FastAPI
import asyncio, os, io
from datetime import datetime
import pytz
from openai import OpenAI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram_sender import send_report, send_alert, send_chart_image

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Report sent to Telegram"}

async def call_grok(prompt: str):
    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content

async def full_report():
    prompt = f"""Create a complete trading report for {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}.

Sections:
1. STOCKS (Indian + Global, small/mid/large cap) - specific buy/sell/hold with quantity, risk, method, indicators, TradingView link, Dhan note
2. COMMODITIES
3. ETFs
4. CRYPTO

Include a long, detailed, powerful Educator Lesson teaching me about the market.

Be precise, educational, and actionable."""

    report = await call_grok(prompt)

    # Send chart
    try:
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot([1,2,3,4,5], [10,25,15,30,20], marker='o')
        ax.set_title("Market Snapshot")
        ax.grid(True)
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        await send_chart_image(buf)
    except:
        pass

    await send_report(report)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
