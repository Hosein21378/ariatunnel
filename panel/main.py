from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="AriaTunnel Panel", version="1.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

DB_FILE = str(BASE_DIR / "aria.db")

def init_db():
    os.makedirs(BASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                traffic_gb REAL DEFAULT 100.0,
                used_gb REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active'
            )''')
    c.execute('''CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                country TEXT,
                status TEXT DEFAULT 'online'
            )''')
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(traffic_gb), SUM(used_gb) FROM users")
    user_stats = c.fetchone()
    c.execute("SELECT * FROM nodes")
    nodes = c.fetchall()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    
    return templates.TemplateResponse(request, "index.html", {
        "total_users": user_stats[0] or 0,
        "total_traffic": round(user_stats[1] or 0, 2),
        "total_used": round(user_stats[2] or 0, 2),
        "nodes": nodes,
        "users": users
    })

@app.post("/add_user")
async def add_user(username: str = Form(...), traffic_gb: float = Form(50.0)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, traffic_gb) VALUES (?, ?)", (username, traffic_gb))
        conn.commit()
    except Exception:
        pass
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/status")
async def api_status():
    return {"status": "ok", "service": "AriaTunnel Panel"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
