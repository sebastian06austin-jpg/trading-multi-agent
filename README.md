# Trading Multi-Agent System (MCP + Render 24/7)

Two Render services:
1. MCP: Start command `python mcp_server.py`
2. Main App: Start command `uvicorn app:app --host 0.0.0.0 --port $PORT`

Add env vars: XAI_API_KEY, TELEGRAM_*, MCP_URL (after first deploy)
Ping both with cron-job.org every 10 min.
