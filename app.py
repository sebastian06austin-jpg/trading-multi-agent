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
    return {"status": "✅ SUCCESS! Ultimate report + chart sent to Telegram"}

async def full_report():
    prompt = f"""Create the ultimate trading report for {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}.

**DISCLAIMER:** This is educational paper-trading only. Not financial advice. Use in Dhan at your own risk. Past performance is not guarantee of future results.

**STOCKS** (Indian + Global, small/mid/large cap)
- Company name + key info
- Best method & indicators to use
- When to buy/sell/hold (long/short)
- Suggested quantity & capital allocation (max 1-2% risk)
- TradingView link + Dhan note

**COMMODITIES**
**ETFs**
**CRYPTO**

**EDUCATOR LESSON** (long, detailed, powerful teaching about trading, market psychology, risk management, Dhan app usage, indicators, etc.)

Be specific, actionable, and educational."""

    try:
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        report = response.choices[0].message.content
    except Exception as e:
        report = f"Error calling Grok: {str(e)}"

    # Chart
    try:
        fig, ax = plt.subplots(figsize=(10,5))
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
    print(f"🚀 Ultimate system starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
