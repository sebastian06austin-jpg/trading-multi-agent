import sqlite3
import json
from datetime import datetime
import os

# Use /tmp folder which is writable on Render free tier
DB_PATH = "/tmp/bot_memory.db"

conn = sqlite3.connect(DB_PATH, check_same_thread=False)

conn.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    preferences TEXT DEFAULT '{"risk_level":"medium","favorites":[],"default_quantity":1,"trading_style":"swing"}',
    memory_summary TEXT,
    last_interaction TEXT
)''')

conn.execute('''CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    content TEXT,
    timestamp TEXT
)''')

def get_user_prefs(user_id):
    row = conn.execute("SELECT preferences FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return json.loads('{"risk_level":"medium","favorites":[],"default_quantity":1,"trading_style":"swing"}')
    return json.loads(row[0])

def set_user_pref(user_id, key, value):
    prefs = get_user_prefs(user_id)
    prefs[key] = value
    conn.execute("UPDATE users SET preferences=?, last_interaction=? WHERE user_id=?", 
                 (json.dumps(prefs), datetime.now().isoformat(), user_id))
    conn.commit()

def save_message(user_id, role, content):
    conn.execute("INSERT INTO chat_history (user_id, role, content, timestamp) VALUES (?,?,?,?)",
                 (user_id, role, content, datetime.now().isoformat()))
    conn.commit()

def get_user_history(user_id, limit=20):
    rows = conn.execute("SELECT role, content FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT ?", 
                        (user_id, limit)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
