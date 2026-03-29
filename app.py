from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio, json, os, io
from datetime import datetime
import pytz
from openai import OpenAI
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from telegram_sender import send_report, send_alert, send_chart_image
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-multi-agent-0309")  # Change anytime here or in Render env

MCP_URL = os.getenv("MCP_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(full_report, 'cron', hour=2, minute=30)   # 8 AM IST
    scheduler.add_job(full_report, 'cron', hour=12, minute=30)  # 6 PM IST
    scheduler.add_job(real_time_check, 'interval', minutes=10)
    scheduler.add_job(sunday_self_review, 'cron', day_of_week='sun', hour=9, minute=0)
    scheduler.start()
    print("🚀 ULTIMATE 24/7 Multi-Agent System LIVE on Render")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "agent_healthy", "model": GROK_MODEL, "time": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()}

@app.get("/trigger-report")
async def trigger_report():
    await full_report()
    return {"status": "✅ SUCCESS! Full report + charts + lesson sent to Telegram"}

# ====================== LANGGRAPH MULTI-AGENT ======================
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    portfolio: dict

def specialist_node(name: str):
    async def node(state):
        prompt_file = f"agents/{name}_prompt.md"
        with open(prompt_file) as f:
            prompt = f.read()
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": state["messages"][-1]}],
            temperature=0.1
        )
        return {"messages": [f"{name.upper()}: {response.choices[0].message.content}"]}
    return node

# Nodes
graph = StateGraph(AgentState)
for agent in ["quant", "technical", "sentiment", "risk", "options", "educator"]:
    graph.add_node(agent, specialist_node(agent))

def supervisor(state):
    all_outputs = "\n\n".join(state["messages"])
    with open("agents/supervisor_prompt.md") as f:
        prompt = f.read()
    final = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": all_outputs}],
        temperature=0.1
    )
    report = final.choices[0].message.content
    # Generate chart
    fig, ax = plt.subplots()
    # Simple example plot — you can expand with real data
    ax.plot([1,2,3], [10,20,15])
    ax.set_title("Watchlist Snapshot")
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    asyncio.create_task(send_chart_image(buf))
    return {"messages": [report]}

graph.add_node("supervisor", supervisor)
graph.set_entry_point("supervisor")
for agent in ["quant", "technical", "sentiment", "risk", "options", "educator"]:
    graph.add_edge("supervisor", agent)  # Parallel
graph.add_edge(["quant", "technical", "sentiment", "risk", "options", "educator"], "supervisor")  # Back to supervisor

app_graph = graph.compile()

async def full_report():
    with open("portfolio.json") as f:
        port = json.load(f)
    prompt = f"Full analysis at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}. Indian + global focus. Use sections: Stocks, Commodities, ETFs, Crypto."
    result = app_graph.invoke({"messages": [prompt], "portfolio": port})
    report = result["messages"][-1]
    await send_report(report)

async def real_time_check():
    # Same as before — meaningful alerts
    prompt = "Quick real-time scan. Return only one line with stock/IPO if STRONG signal."
    alert_text = client.chat.completions.create(model=GROK_MODEL, messages=[{"role": "user", "content": prompt}]).choices[0].message.content
    if "STRONG" in alert_text.upper():
        await send_alert(alert_text)

async def sunday_self_review():
    prompt = "Sunday self-review: Analyze last week's signals, win-rate, lessons learned."
    review = client.chat.completions.create(model=GROK_MODEL, messages=[{"role": "user", "content": prompt}]).choices[0].message.content
    await send_report(f"📅 SUNDAY SELF-REVIEW\n\n{review}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
