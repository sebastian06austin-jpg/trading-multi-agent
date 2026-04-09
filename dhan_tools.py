from dhanhq import dhanhq
import json
import os

DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN) if DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN else None

def get_dhan_live_quote(symbol: str) -> str:
    """Get live quote from Dhan"""
    if not dhan:
        return "❌ Dhan not configured. Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in Render env vars."
    try:
        data = dhan.get_quote(symbol)
        return json.dumps(data)
    except Exception as e:
        return f"Error fetching quote: {str(e)}"

def get_dhan_portfolio() -> str:
    """Get live portfolio and positions from Dhan"""
    if not dhan:
        return "❌ Dhan not configured."
    try:
        holdings = dhan.get_holdings()
        positions = dhan.get_positions()
        return json.dumps({"holdings": holdings, "positions": positions})
    except Exception as e:
        return f"Error fetching portfolio: {str(e)}"
