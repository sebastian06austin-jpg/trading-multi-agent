from fastmcp import FastMCP
import json, os, yfinance as yf
from datetime import datetime
import pytz

mcp = FastMCP("trading-mcp")

@mcp.tool()
def get_nse_data(ticker: str, period: str = "1d") -> str:
    """Get price data for any NSE stock/index (.NS suffix automatic)"""
    data = yf.download(ticker if ".NS" in ticker else ticker + ".NS", period=period)
    return data.to_json()

@mcp.tool()
def update_portfolio(action: str, ticker: str, qty: float, price: float, reason: str) -> str:
    """Update virtual portfolio (buy/sell). Action='buy' or 'sell'"""
    path = "portfolio.json"
    with open(path, "r") as f:
        port = json.load(f)
    # ... simple logic to update capital, holdings, log trade
    with open(path, "w") as f:
        json.dump(port, f, indent=2)
    return "Portfolio updated"

@mcp.tool()
def calculate_risk_metrics() -> str:
    """ATR, VaR, Kelly sizing etc."""
    # implement simple calcs or call code interpreter via xAI
    return "Risk metrics calculated"

mcp.run(host="0.0.0.0", port=8000)
