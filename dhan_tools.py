from dhanhq import dhanhq
import json
import os

dhan = None

def init_dhan():
    global dhan
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    if client_id and access_token:
        dhan = dhanhq(client_id, access_token)
        print("✅ Dhan connected")
    else:
        print("⚠️ No Dhan credentials in env vars")

init_dhan()

def get_dhan_portfolio() -> str:
    if not dhan:
        return "❌ Dhan not configured in Render env vars"
    try:
        holdings = dhan.get_holdings()
        positions = dhan.get_positions()
        return json.dumps({"holdings": holdings, "positions": positions}, default=str)
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_trade_history() -> str:
    if not dhan:
        return "❌ Dhan not configured in Render env vars"
    try:
        if hasattr(dhan, 'get_order_list'):
            data = dhan.get_order_list()
        elif hasattr(dhan, 'get_orders'):
            data = dhan.get_orders()
        else:
            data = "No order history method"
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"❌ Error: {str(e)}"
