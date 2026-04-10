from dhanhq import dhanhq
import json
import os

DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN) if DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN else None

def get_dhan_live_quote(symbol: str) -> str:
    if not dhan:
        return "❌ Dhan not configured"
    try:
        data = dhan.get_quote(symbol)
        return json.dumps(data)
    except Exception as e:
        return f"Error: {str(e)}"

def get_dhan_portfolio() -> str:
    if not dhan:
        return "❌ Dhan not configured"
    try:
        holdings = dhan.get_holdings()
        positions = dhan.get_positions()
        return json.dumps({"holdings": holdings, "positions": positions}, default=str)
    except Exception as e:
        return f"Error: {str(e)}"

def get_trade_history() -> str:
    """Robust trade history with multiple fallback methods"""
    if not dhan:
        return "❌ Dhan not configured"
    try:
        # Try different possible methods
        if hasattr(dhan, 'get_order_list'):
            orders = dhan.get_order_list()
        elif hasattr(dhan, 'get_orders'):
            orders = dhan.get_orders()
        elif hasattr(dhan, 'get_order_history'):
            orders = dhan.get_order_history()
        else:
            orders = None

        if orders and len(orders) > 0:
            return json.dumps(orders, indent=2, default=str)
        else:
            return "No recent orders found (or history not available in this Dhan API version)"
    except Exception as e:
        return f"Could not fetch trade history.\nError: {str(e)}"
