from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import sqlite3
import subprocess
import signal
import sys
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
    cols = [r[1] for r in c.execute("PRAGMA table_info(nodes)")]
    if "local_port" not in cols:
        c.execute("ALTER TABLE nodes ADD COLUMN local_port INTEGER")
    if "pid" not in cols:
        c.execute("ALTER TABLE nodes ADD COLUMN pid INTEGER")
    if "secret" not in cols:
        c.execute("ALTER TABLE nodes ADD COLUMN secret TEXT")
    if "dest" not in cols:
        c.execute("ALTER TABLE nodes ADD COLUMN dest TEXT DEFAULT '1.1.1.1:443'")
    if "transport" not in cols:
        c.execute("ALTER TABLE nodes ADD COLUMN transport TEXT DEFAULT 'tcp'")
    conn.commit()
    conn.close()

init_db()

CORE_CLIENT = str(BASE_DIR.parent / "core" / "client.py")
SECRET_FILE = "/etc/ariatunnel.secret"

def _secret():
    try:
        return Path(SECRET_FILE).read_text().strip()
    except Exception:
        return os.getenv("TUNNEL_SECRET", "AriaTunnelSecureKey2026!")

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

@app.post("/add_node")
async def add_node(name: str = Form(...), ip: str = Form(...), country: str = Form("Turkey"),
                   secret: str = Form(""), dest: str = Form("1.1.1.1:443"),
                   transport: str = Form("tcp"), listen_port: int = Form(0)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO nodes (name, ip, country, status, secret, dest, transport, local_port) VALUES (?, ?, ?, 'offline', ?, ?, ?, ?)",
                  (name, ip, country, secret or None, dest, transport, listen_port or 0))
        conn.commit()
    except Exception:
        pass
    conn.close()
    return RedirectResponse(url="/", status_code=303)

def _alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False

@app.post("/connect/{node_id}")
async def connect_node(node_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    row = c.execute("SELECT ip, local_port, pid, secret, dest, transport FROM nodes WHERE id=?", (node_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "node not found")
    ip, local_port, pid, node_secret, dest, transport = row
    if _alive(pid):
        conn.close()
        return RedirectResponse(url="/", status_code=303)
    local_port = local_port or (10800 + node_id)
    env = dict(os.environ, SERVER_HOST=ip, SERVER_PORT=os.getenv("TUNNEL_PORT", "8443"),
               LOCAL_PORT=str(local_port), TUNNEL_SECRET=node_secret or _secret(),
               TARGET_DEST=dest or "1.1.1.1:443", TUNNEL_TRANSPORT=transport or "tcp")
    proc = subprocess.Popen([sys.executable, CORE_CLIENT], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    c.execute("UPDATE nodes SET local_port=?, pid=?, status='online' WHERE id=?",
              (local_port, proc.pid, node_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/disconnect/{node_id}")
async def disconnect_node(node_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    row = c.execute("SELECT pid FROM nodes WHERE id=?", (node_id,)).fetchone()
    if row and row[0]:
        try:
            os.kill(row[0], signal.SIGTERM)
        except Exception:
            pass
    c.execute("UPDATE nodes SET pid=NULL, status='offline' WHERE id=?", (node_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/status")
async def api_status():
    return {"status": "ok", "service": "AriaTunnel Panel"}
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
