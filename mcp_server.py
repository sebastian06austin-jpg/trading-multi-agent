from fastmcp import FastMCP
import json, os, yfinance as yf
from datetime import datetime
import pytz
from starlette.responses import JSONResponse
import asyncio
from dhanhq import dhanhq

mcp = FastMCP("trading-mcp")

# Dhan configuration (production or sandbox)
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
DHAN_BASE_URL = os.getenv("DHAN_BASE_URL", "https://api.dhan.co/v2")  # change to sandbox.dhan.co/v2 if needed

dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN) if DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN else None

# === OLD TOOLS + NEW DHAN TOOLS ===
@mcp.tool()
def get_nse_data(ticker: str, period: str = "1d") -> str:
    t = ticker if ".NS" in ticker else ticker + ".NS"
    data = yf.download(t, period=period, progress=False)
    return data.to_json()

@mcp.tool()
def get_dhan_live_quote(symbol: str) -> str:
    if not dhan:
        return "❌ Dhan not configured"
    try:
        data = dhan.get_quote(symbol)
        return json.dumps(data)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_dhan_portfolio() -> str:
    if not dhan:
        return "❌ Dhan not configured"
    try:
        holdings = dhan.get_holdings()
        positions = dhan.get_positions()
        return json.dumps({"holdings": holdings, "positions": positions})
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({
        "status": "mcp_healthy",
        "dhan_configured": bool(dhan),
        "time": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
    })

async def main():
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 MCP Server starting on Render → http://0.0.0.0:{port}")
    await mcp.run_http_async(transport="http", host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())
