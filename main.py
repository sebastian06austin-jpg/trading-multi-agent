import json, os
from datetime import datetime
import pytz
from graph import app
from telegram_sender import send_report
from tools.custom_tools import get_nse_data

# Load portfolio
with open("portfolio.json") as f:
    port = json.load(f)

# Pre-fetch data (India focus)
watchlist = ["^NSEI", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]
data_summary = {t: get_nse_data.invoke({"ticker": t}) for t in watchlist}

user_input = f"""
Today: {datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M IST')}
Virtual capital: ₹{port['capital']}
Watchlist data: {data_summary}
Analyze Nifty + watchlist. Follow report_template.md exactly.
"""

result = app.invoke({"messages": [user_input], "portfolio": port})

final_report = result["messages"][-1]

# Send
import asyncio
asyncio.run(send_report(final_report))

# Auto-commit happens in GitHub Actions
print("✅ Report generated and sent!")