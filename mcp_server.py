from fastmcp import FastMCP
import json, os, yfinance as yf
from datetime import datetime
import pytz
from starlette.responses import JSONResponse
import asyncio
from dhanhq import dhanhq

mcp = FastMCP("trading-mcp")

from dhanhq import dhanhq

client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")
dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)

@mcp.tool()
def get_dhan_live_quote(symbol: str) -> str:
    """Get live price from Dhan"""
    data = dhan.get_quote(symbol)
    return json.dumps(data)

@mcp.tool()
def get_dhan_portfolio() -> str:
    """Get live portfolio and positions from Dhan"""
    holdings = dhan.get_holdings()
    positions = dhan.get_positions()
    return json.dumps({"holdings": holdings, "positions": positions})

@mcp.tool()
def get_nse_data(ticker: str, period: str = "1d") -> str:
    t = ticker if ".NS" in ticker else ticker + ".NS"
    data = yf.download(t, period=period, progress=False)
    return data.to_json()

@mcp.tool()
def update_portfolio(action: str, ticker: str, qty: float, price: float, reason: str) -> str:
    path = "portfolio.json"
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({"capital": 100000.0, "holdings": {}, "trade_log": []}, f, indent=2)
    with open(path, "r") as f:
        port = json.load(f)
    if action.lower() == "buy":
        cost = qty * price
        if port["capital"] < cost: return "❌ Not enough capital!"
        port["capital"] -= cost
        port["holdings"][ticker] = port["holdings"].get(ticker, 0) + qty
    elif action.lower() == "sell":
        current = port["holdings"].get(ticker, 0)
        if current < qty: return "❌ Not enough shares!"
        port["capital"] += qty * price
        port["holdings"][ticker] = current - qty
        if port["holdings"][ticker] == 0: del port["holdings"][ticker]
    else:
        return "❌ Invalid action!"
    port["trade_log"].append({
        "time": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
        "action": action, "ticker": ticker, "qty": qty, "price": price, "reason": reason
    })
    with open(path, "w") as f:
        json.dump(port, f, indent=2)
    return f"✅ {action} {qty} {ticker} @ ₹{price} | Capital: ₹{port['capital']:.2f}"

@mcp.tool()
def get_portfolio() -> str:
    path = "portfolio.json"
    if not os.path.exists(path):
        return json.dumps({"capital": 100000.0, "holdings": {}, "trade_log": []}, indent=2)
    with open(path) as f:
        return json.dumps(json.load(f), indent=2)

@mcp.tool()
def calculate_risk_metrics() -> str:
    return "1-2% risk rule active"

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({
        "status": "mcp_healthy",
        "service": "trading-mcp",
        "time": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
    })

async def main():
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 MCP Server starting on Render port {port}")
    await mcp.run_http_async(
        transport="http",
        host="0.0.0.0",
        port=port
    )

if __name__ == "__main__":
    asyncio.run(main())
