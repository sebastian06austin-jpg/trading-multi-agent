from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio, json, os, traceback
from datetime import datetime
import pytz
from xai_sdk import Client
from xai_sdk.chat import user, tool_result
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram_sender import send_report, send_alert, send_chart_image
from database import get_user_prefs, set_user_pref, save_message, get_user_history
from dhan_tools import get_dhan_live_quote, get_dhan_portfolio, get_trade_history

# ====================== INITIALIZATION ======================
client = None
try:
    client = Client(api_key=os.getenv("XAI_API_KEY"))
    print("✅ xAI SDK initialized successfully")
except Exception as e:
    print(f"❌ xAI SDK init failed: {e}")

GROK_MODEL = "grok-4.20-multi-agent-0309"

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
    print(f"🚀 BULLETPROOF GROK 4.20 MULTI-AGENT SYSTEM LIVE → Using {GROK_MODEL}")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": GROK_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    try:
        print("🚀 /trigger-report called - starting full_report")
        await full_report()
        print("✅ full_report completed successfully")
        return {"status": "✅ SUCCESS!"}
    except Exception as e:
        print(f"❌ /trigger-report failed: {traceback.format_exc()}")
        return {"status": "❌ Error", "detail": str(e)}

@app.get("/reset-db")
async def reset_database():
    try:
        if os.path.exists("bot_memory.db"):
            os.remove("bot_memory.db")
            await send_alert("🗑️ Database & all chat history cleared successfully.")
        else:
            await send_alert("✅ Database was already clean.")
        return {"status": "Database reset complete."}
    except Exception as e:
        print(f"❌ /reset-db failed: {traceback.format_exc()}")
        return {"status": f"Error: {str(e)}"}

# Direct commands and Telegram webhook (unchanged)
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

        if text in ["/portfolio", "portfolio", "holdings", "positions"]:
            data = get_dhan_portfolio()
            await send_alert(f"📊 **Live Dhan Portfolio:**\n{data}")
            return {"status": "ok"}

        if text in ["/tradehistory", "trade history", "orders", "history"]:
            data = get_trade_history()
            await send_alert(f"📜 **Dhan Trade History:**\n{data}")
            return {"status": "ok"}

        if text.startswith("/quote"):
            symbol = text.split()[-1].upper() if len(text.split()) > 1 else "RELIANCE"
            data = get_dhan_live_quote(symbol)
            await send_alert(f"📈 Live Quote for {symbol}:\n{data}")
            return {"status": "ok"}

        # Multi-Agent call
        dhan_data = get_dhan_portfolio()
        system = f"""You are Grok 4.20 Multi-Agent — truth-seeking, highly intelligent, with deep knowledge of finance, macroeconomics, valuation, risk management, behavioral finance, SEBI regulations, and Indian/global markets.
You have full real-time access to the user's Dhan account. Current portfolio: {dhan_data}.
User preferences: {json.dumps(prefs)}.

When you need data, output ONLY a JSON object like this:
{{"tool": "get_dhan_portfolio"}}
or
{{"tool": "get_dhan_live_quote", "symbol": "RELIANCE"}}

After you receive the tool result, give your final intelligent answer."""

        reply = await call_grok(f"{system}\n\nUser: {text}")
        save_message(user_id, "assistant", reply)
        await send_alert(reply)
        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Telegram webhook error: {traceback.format_exc()}")
        return {"status": "ok"}

async def call_grok(prompt: str):
    if client is None:
        return "❌ xAI SDK not initialized."
    try:
        print("📤 Calling Grok with prompt length:", len(prompt))
        chat = client.chat.create(model=GROK_MODEL)
        chat.append(user(prompt))

        final_content = "**No response from model**"
        for response in chat.stream():
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        result = tool_map[func_name](**args) if args else tool_map[func_name]()
                        print(f"🔧 Tool called: {func_name} → success")
                        chat.append(tool_result(str(result)))
                    except Exception as e:
                        print(f"🔧 Tool error {func_name}: {e}")
                        chat.append(tool_result(f"Tool error: {str(e)}"))
            else:
                final_content = response.content or "**Empty response from Grok**"
                print("📥 Received final content from Grok:", repr(final_content[:200]))
                break

        return final_content
    except Exception as e:
        print(f"❌ call_grok failed: {traceback.format_exc()}")
        return f"❌ Grok API error: {str(e)}"

async def full_report():
    try:
        print("📊 Starting full_report")
        dhan_data = get_dhan_portfolio()
        prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Use live Dhan data: {dhan_data}. Include Stocks, Commodities, ETFs, Crypto with precise recommendations + long Educator lesson + TradingView links."
        
        report = await call_grok(prompt)
        print("📤 Report generated, length:", len(report))
        print("📤 First 300 chars of report:", repr(report[:300]))
        
        await send_report(report)
        print("✅ Report sent to Telegram successfully")
    except Exception as e:
        print(f"❌ full_report failed: {traceback.format_exc()}")
        await send_alert(f"❌ Report generation failed: {str(e)}")

async def sunday_self_review():
    try:
        review = await call_grok("Sunday self-review of last week signals, lessons, improvements, and portfolio performance.")
        await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")
    except Exception as e:
        print(f"❌ sunday_self_review failed: {traceback.format_exc()}")
        await send_alert(f"❌ Sunday review failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
