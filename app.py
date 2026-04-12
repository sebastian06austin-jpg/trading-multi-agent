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
GROK_MODEL = "grok-beta"   # Stable model that supports tool calling (multi-agent models are restricted by xAI)

tool_map = {
    "get_dhan_live_quote": get_dhan_live_quote,
    "get_dhan_portfolio": get_dhan_portfolio,
    "get_trade_history": get_trade_history,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)
    scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=10, minute=0)
    scheduler.start()
    print(f"🚀 GROK MULTI-AGENT TOOL ORCHESTRATION SYSTEM LIVE → Using {GROK_MODEL}")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS!"}

@app.get("/reset-db")
async def reset_database():
    try:
        import os
        if os.path.exists("bot_memory.db"):
            os.remove("bot_memory.db")
            await send_alert("🗑️ Database & all chat history cleared successfully. Bot restarted fresh.")
            print("✅ Database deleted")
        else:
            await send_alert("✅ Database was already clean.")
        return {"status": "Database reset complete."}
    except Exception as e:
        return {"status": f"Error: {str(e)}"}

@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    data = await request.json()
    await send_alert(f"📢 TradingView Alert: {data.get('message', 'New signal')}")
    return {"status": "received"}

@app.post("/dhan-postback")
async def dhan_postback(request: Request):
    try:
        data = await request.json()
        status = data.get("orderStatus", "")
        symbol = data.get("tradingSymbol", "Unknown")
        if status in ["TRADED", "REJECTED", "CANCELLED", "PENDING"]:
            await send_alert(f"📨 Dhan Order Update\nSymbol: {symbol}\nStatus: {status}")
        return {"status": "received"}
    except Exception as e:
        print("Dhan postback error:", str(e))
        return {"status": "received"}

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

        if text == "/portfolio" or "portfolio" in text or "holdings" in text or "positions" in text:
            data = get_dhan_portfolio()
            await send_alert(f"📊 **Live Dhan Portfolio:**\n{data}")
            return {"status": "ok"}

        if text == "/tradehistory" or "trade history" in text or "orders" in text or "history" in text:
            data = get_trade_history()
            await send_alert(f"📜 **Dhan Trade History:**\n{data}")
            return {"status": "ok"}

        if text.startswith("/quote"):
            symbol = text.split()[-1].upper() if len(text.split()) > 1 else "RELIANCE"
            data = get_dhan_live_quote(symbol)
            await send_alert(f"📈 Live Quote for {symbol}:\n{data}")
            return {"status": "ok"}

        dhan_data = get_dhan_portfolio()
        system = f"""You are Grok 4.20 Multi-Agent — truth-seeking, highly intelligent, with deep knowledge of finance, macroeconomics, valuation, risk management, behavioral finance, SEBI regulations, and Indian/global markets.
You have full real-time access to the user's Dhan account. Current portfolio: {dhan_data}.
User preferences: {json.dumps(prefs)}.
You can use tools by outputting ONLY a JSON object like this:
{{"tool": "get_dhan_portfolio"}}
or
{{"tool": "get_dhan_live_quote", "symbol": "RELIANCE"}}
After you get the tool result, give your final answer."""

        reply = await call_grok(f"{system}\n\nUser: {text}")
        save_message(user_id, "assistant", reply)
        await send_alert(reply)
        return {"status": "ok"}

    except Exception as e:
        print("Webhook error:", str(e))
        return {"status": "ok"}

async def call_grok(prompt: str):
    messages = [{"role": "user", "content": prompt}]
    
    for _ in range(6):
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=messages,
            temperature=0.7
        )
        message_content = response.choices[0].message.content
        messages.append({"role": "assistant", "content": message_content})

        if "{" in message_content and "tool" in message_content.lower():
            try:
                start = message_content.find("{")
                end = message_content.rfind("}") + 1
                tool_call = json.loads(message_content[start:end])
                func_name = tool_call.get("tool")
                if func_name in tool_map:
                    args = {k: v for k, v in tool_call.items() if k != "tool"}
                    result = tool_map[func_name](**args) if args else tool_map[func_name]()
                    messages.append({"role": "tool", "content": str(result)})
                    continue
            except Exception as e:
                print("Tool parsing error:", str(e))
        else:
            return message_content

    return messages[-1]["content"]

async def full_report():
    dhan_data = get_dhan_portfolio()
    prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Use live Dhan data: {dhan_data}. Include Stocks, Commodities, ETFs, Crypto with precise recommendations + long Educator lesson + TradingView links."
    report = await call_grok(prompt)
    await send_report(report)

async def sunday_self_review():
    review = await call_grok("Sunday self-review of last week signals, lessons, improvements, and portfolio performance.")
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
