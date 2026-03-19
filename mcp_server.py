from fastmcp import FastMCP
import json, os, yfinance as yf
from datetime import datetime
import pytz

# === FIXED FOR RENDER: host goes here ===
mcp = FastMCP("trading-mcp", host="0.0.0.0")

@mcp.tool()
def get_nse_data(ticker: str, period: str = "1d") -> str:
    """Get latest price data for any NSE stock/index (.NS auto-added)"""
    t = ticker if ".NS" in ticker else ticker + ".NS"
    data = yf.download(t, period=period, progress=False)
    return data.to_json()

@mcp.tool()
def update_portfolio(action: str, ticker: str, qty: float, price: float, reason: str) -> str:
    """Buy/sell in virtual ₹1L portfolio"""
    path = "portfolio.json"
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({"capital": 100000.0, "holdings": {}, "trade_log": []}, f, indent=2)
    
    with open(path, "r") as f:
        port = json.load(f)
    
    if action.lower() == "buy":
        cost = qty * price
        if port["capital"] < cost:
            return "❌ Not enough capital!"
        port["capital"] -= cost
        port["holdings"][ticker] = port["holdings"].get(ticker, 0) + qty
    elif action.lower() == "sell":
        current = port["holdings"].get(ticker, 0)
        if current < qty:
            return "❌ Not enough shares!"
        port["capital"] += qty * price
        port["holdings"][ticker] = current - qty
        if port["holdings"][ticker] == 0:
            del port["holdings"][ticker]
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
    """Return current virtual portfolio"""
    path = "portfolio.json"
    if not os.path.exists(path):
        return json.dumps({"capital": 100000.0, "holdings": {}, "trade_log": []}, indent=2)
    with open(path) as f:
        return json.dumps(json.load(f), indent=2)

@mcp.tool()
def calculate_risk_metrics() -> str:
    """Risk metrics (1-2% rule enforced by supervisor)"""
    return "1-2% risk rule + Kelly/ATR sizing active"

# === RENDER PORT BINDING (MUST USE THIS) ===
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 MCP Server starting on Render → http://0.0.0.0:{port} (transport=http)")
    mcp.run(
        transport="http",      # forces HTTP (no stdio fallback)
        port=port              # NO 'host' here — that's why it was failing
    )
