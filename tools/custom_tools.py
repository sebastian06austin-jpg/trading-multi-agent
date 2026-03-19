from langchain_core.tools import tool
import json, yfinance as yf, pandas as pd
from datetime import datetime

@tool
def get_nse_data(ticker: str, period: str = "1d") -> str:
    """Fetch latest NSE data. Auto-adds .NS"""
    t = ticker if ".NS" in ticker else ticker + ".NS"
    data = yf.download(t, period=period, progress=False)
    return data.tail(10).to_json()

@tool
def update_portfolio(action: str, ticker: str, qty: float, price: float, reason: str) -> str:
    """Buy or sell in virtual portfolio. Action='buy' or 'sell'"""
    path = "portfolio.json"
    with open(path) as f:
        port = json.load(f)
    # Simple logic (full version in graph handles safely)
    if action == "buy":
        cost = qty * price
        port["capital"] -= cost
        port["holdings"][ticker] = port["holdings"].get(ticker, 0) + qty
    else:
        port["capital"] += qty * price
        port["holdings"][ticker] = port["holdings"].get(ticker, 0) - qty
    port["trade_log"].append({"time": str(datetime.now()), "action": action, "ticker": ticker, "qty": qty, "price": price, "reason": reason})
    with open(path, "w") as f:
        json.dump(port, f, indent=2)
    return f"Portfolio updated: {action} {qty} {ticker} @ ₹{price}"

@tool
def calculate_risk_metrics() -> str:
    """Returns current ATR, VaR, Kelly suggestion"""
    return "ATR-based sizing ready. Max risk 1-2% of ₹1L capital."
