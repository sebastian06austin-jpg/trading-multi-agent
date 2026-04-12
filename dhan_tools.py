from dhanhq import dhanhq
import json
import os

# Global Dhan client (initialized once)
dhan = None

def init_dhan():
    global dhan
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    if client_id and access_token:
        dhan = dhanhq(client_id, access_token)
        print("✅ Dhan connected successfully")
    else:
        print("⚠️ Dhan credentials missing in env vars")

init_dhan()

def get_dhan_live_quote(symbol: str) -> str:
    if not dhan:
        return "❌ Dhan not connected"
    try:
        data = dhan.get_quote(symbol)
        return json.dumps(data, default=str)
    except Exception as e:
        return f"Error: {str(e)}"

def get_dhan_portfolio() -> str:
    if not dhan:
        return "❌ Dhan not connected"
    try:
        holdings = dhan.get_holdings()
        positions = dhan.get_positions()
        return json.dumps({"holdings": holdings, "positions": positions}, default=str)
    except Exception as e:
        return f"Error: {str(e)}"

def get_trade_history() -> str:
    if not dhan:
        return "❌ Dhan not connected"
    try:
        # Try all possible methods for trade/order history
        if hasattr(dhan, 'get_order_list'):
            data = dhan.get_order_list()
        elif hasattr(dhan, 'get_orders'):
            data = dhan.get_orders()
        elif hasattr(dhan, 'get_order_history'):
            data = dhan.get_order_history()
        else:
            return "Dhan API does not support trade history on your account"
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Could not fetch trade history: {str(e)}"
