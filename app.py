from fastapi import FastAPI, Request
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

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS!"}

# Telegram Webhook (simple and robust)
@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            user_id = str(update["message"]["from"]["id"])
            
            save_message(user_id, "user", text)
            
            prefs = get_user_prefs(user_id)
            
            # Auto preference update
            if "risk" in text.lower():
                risk = "low" if "low" in text.lower() else "high" if "high" in text.lower() else "medium"
                set_user_pref(user_id, "risk_level", risk)
                # Send reply
                await send_alert(f"✅ Risk level updated to **{risk}**")
                return {"status": "ok"}
            
            # Normal Grok reply
            history = get_user_history(user_id)
            system = f"You are Grok. User preferences: {json.dumps(prefs)}. Be helpful, trading-focused."
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
    prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Use live Dhan data: {dhan_data}. Include Stocks, Commodities, ETFs, Crypto with precise recommendations + long Educator lesson."
    report = await call_grok(prompt)
    await send_report(report)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
