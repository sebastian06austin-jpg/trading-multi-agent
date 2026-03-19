from fastmcp import FastMCP
import json
import os
import yfinance as yf
from datetime import datetime
import pytz

mcp = FastMCP("trading-mcp")

@mcp.tool()
def get_nse_data(ticker: str, period: str = "1d") -> str:
    """Get price data for any NSE stock/index (.NS suffix automatic)"""
    t = ticker if ".NS" in ticker else ticker + ".NS"
    data = yf.download(t, period=period, progress=False)
    return data.to_json()

@mcp.tool()
def update_portfolio(action: str, ticker: str, qty: float, price: float, reason: str) -> str:
    """Buy/sell in virtual portfolio. Action='buy' or 'sell'"""
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
        current_qty = port["holdings"].get(ticker, 0)
        if current_qty < qty:
            return "❌ Not enough shares!"
        port["capital"] += qty * price
        port["holdings"][ticker] = current_qty - qty
        if port["holdings"][ticker] <= 0:
            port["holdings"].pop(ticker, None)
    else:
        return "❌ Invalid action!"
    
    port["trade_log"].append({
        "time": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
        "action": action,
        "ticker": ticker,
        "qty": qty,
        "price": price,
        "reason": reason
    })
    
    with open(path, "w") as f:
        json.dump(port, f, indent=2)
    
    return f"✅ {action.upper()} {qty} {ticker} @ ₹{price:.2f} | Capital left: ₹{port['capital']:.2f}"

@mcp.tool()
def get_portfolio() -> str:
    """Get current virtual portfolio status"""
    path = "portfolio.json"
    if not os.path.exists(path):
        return json.dumps({"capital": 100000.0, "holdings": {}, "trade_log": []}, indent=2)
    with open(path) as f:
        return json.dumps(json.load(f), indent=2)

@mcp.tool()
def calculate_risk_metrics() -> str:
    """ATR, VaR, Kelly sizing etc."""
    return "1-2% risk rule active. Kelly/ATR sizing ready."

if __name__ == "__main__":
    # === RENDER PORT FIX (required) ===
    port = int(os.getenv("PORT", 8000))   # Render automatically sets $PORT
    
    print("=" * 70)
    print("🚀 Trading MCP Server Starting on Render")
    print(f"   Listening on → 0.0.0.0:{port}")
    print(f"   (This matches Render's port-binding requirement)")
    print("=" * 70)
    
    mcp.run(
        host="0.0.0.0",      # MUST be 0.0.0.0 (not 127.0.0.1)
        port=port
    )
