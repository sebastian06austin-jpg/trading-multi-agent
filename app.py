from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio, json, os, traceback
from datetime import datetime
import pytz
from xai_sdk import Client
from xai_sdk.chat import user, tool_result
from config import TIERS, DEFAULT_RISK_PERCENT, FREE_TRIAL_PROMPTS
from telegram_sender import send_report, send_alert
from database import get_user_prefs, set_user_pref, save_message, get_user_history, get_user_tier, set_user_tier, get_user_info, save_user_info, get_free_prompts_used, increment_free_prompts
from market_tools import get_finnhub_quote, get_finnhub_company_profile, get_finnhub_news, get_finnhub_market_status

client = Client(api_key=os.getenv("XAI_API_KEY"))

GROK_BETA_MODEL = "grok-beta"                    # ← Cheap & fast for public + basic/premium
GROK_ULTRA_MODEL = "grok-4.20-multi-agent-0309"  # ← Only for Ultra tier private chats

tool_map = {
    "get_finnhub_quote": get_finnhub_quote,
    "get_finnhub_company_profile": get_finnhub_company_profile,
    "get_finnhub_news": get_finnhub_news,
    "get_finnhub_market_status": get_finnhub_market_status,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)
    scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=10, minute=0)
    scheduler.start()
    print("🚀 GROK TRADING PRO — Dual Model + Finnhub LIVE")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "beta_model": GROK_BETA_MODEL, "ultra_model": GROK_ULTRA_MODEL}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS!"}

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
        if "message" not in update or "text" not in update["message"]:
            return {"status": "ok"}

        message = update["message"]
        text = message["text"].strip()
        chat_type = message.get("chat", {}).get("type", "private")
        user_id = str(message["from"]["id"])
        lower_text = text.lower()

        print(f"📨 Webhook received → Chat type: {chat_type} | User: {user_id} | Text: {text[:100]}")

        # === PUBLIC CHANNEL / GROUP → IGNORE (only reports allowed) ===
        if chat_type != "private":
            print("🔇 Public message ignored (reports only)")
            return {"status": "ok"}

        # === PRIVATE CHAT ONLY FROM HERE ===
        save_message(user_id, "user", text)

        tier_key = get_user_tier(user_id) or "basic"
        user_info = get_user_info(user_id)
        free_used = get_free_prompts_used(user_id)

        print(f"👤 User tier: {tier_key} | Free used: {free_used}")

        # === /start and /help → Show full tier description ===
        if lower_text in ["/start", "/help"]:
            help_text = (
                "🌍 **Welcome to Grok Trading Pro**\n\n"
                "• **Basic** (Free): 5 private messages + daily public reports\n"
                "• **Premium** (/premium): More details + charts + teaching\n"
                "• **Ultra** (/ultra): Full multi-agent Grok 4.20 + unlimited private chat\n\n"
                "Reply with your market (stocks/forex/crypto etc.), location, and platform to start."
            )
            await send_alert(help_text)
            return {"status": "ok"}

        # === Tier upgrade commands ===
        if lower_text == "/upgrade":
            await send_alert("🌟 Choose tier:\n/premium\n/ultra")
            return {"status": "ok"}
        if lower_text == "/premium":
            set_user_tier(user_id, "premium")
            await send_alert("✅ Premium tier activated!")
            return {"status": "ok"}
        if lower_text == "/ultra":
            set_user_tier(user_id, "ultra")
            await send_alert("✅ Ultra tier activated! Now using full multi-agent Grok.")
            return {"status": "ok"}

        # === Onboarding for new users ===
        if not user_info and lower_text not in ["/start", "/help", "/upgrade", "/premium", "/ultra"]:
            await send_alert("🌍 Welcome! Please tell me:\n1. Your main trading market (stocks/forex/crypto/commodities/futures/options)\n2. Your location\n3. Your trading platform")
            return {"status": "ok"}

        # === Direct commands ===
        if lower_text.startswith("/quote"):
            symbol = lower_text.split()[-1].upper() if len(lower_text.split()) > 1 else "AAPL"
            data = get_finnhub_quote(symbol)
            await send_alert(f"📈 Live Quote for {symbol}:\n{data}")
            return {"status": "ok"}

        # === Decide model based on tier ===
        model_to_use = GROK_ULTRA_MODEL if tier_key == "ultra" else GROK_BETA_MODEL
        print(f"🤖 Using model: {model_to_use}")

        if tier_key == "basic" and free_used < FREE_TRIAL_PROMPTS:
            increment_free_prompts(user_id)

        system = f"""You are Grok. User tier: {tier_key}. Market: {user_info.get('market', 'global') if user_info else 'unknown'}.
STRICT RISK RULE: Never risk more than {DEFAULT_RISK_PERCENT}% of capital. Always calculate exact position size.
Be extremely detailed, educational, and global-aware."""

        reply = await call_grok(f"{system}\n\nUser: {text}", model=model_to_use)
        save_message(user_id, "assistant", reply)
        await send_alert(reply)
        print("✅ Reply sent to user")
        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Webhook CRITICAL ERROR: {traceback.format_exc()}")
        return {"status": "ok"}

async def call_grok(prompt: str, model: str):
    try:
        print(f"📤 [call_grok] Calling {model}...")
        chat = client.chat.create(model=model)
        chat.append(user(prompt))

        full_response = ""
        for response, chunk in chat.stream():
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                print(f"📥 Chunk received → total length: {len(full_response)}")
            elif hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"🔧 Tool call detected")
                for tool_call in response.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        result = tool_map[func_name](**args) if args else tool_map[func_name]()
                        chat.append(tool_result(str(result)))
                    except Exception as e:
                        chat.append(tool_result(f"Tool error: {str(e)}"))

        print(f"📤 [call_grok] Final response length: {len(full_response)}")
        return full_response.strip() or "**Empty response from Grok**"
    except Exception as e:
        print(f"❌ [call_grok] ERROR: {traceback.format_exc()}")
        return f"❌ Grok error: {str(e)}"

async def full_report():
    try:
        print("📊 [full_report] Starting (using grok-beta for scalability)")
        prompt = f"Full global analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Include Stocks, Commodities, ETFs, Crypto, Forex, Futures with precise recommendations + long Educator lesson + TradingView links. Enforce 1% risk rule."
        report = await call_grok(prompt, GROK_BETA_MODEL)
        await send_report(report)
        print("✅ Report sent to public channel")
    except Exception as e:
        print(f"❌ full_report failed: {traceback.format_exc()}")
        await send_alert(f"❌ Report failed: {str(e)}")

async def sunday_self_review():
    review = await call_grok("Sunday self-review of last week signals, lessons, improvements, and portfolio performance with strict risk rule adherence.", GROK_BETA_MODEL)
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
