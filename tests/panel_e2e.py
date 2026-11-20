#!/usr/bin/env python3
"""Integration check: panel -> add node -> connect -> real data through tunnel -> disconnect."""
import asyncio, os, socket, subprocess, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECHO, TUN, PANEL = 19999, 18443, 18000
SECRET = "panel-integration-secret"

def up(port, timeout=25):
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False

def post(path, data):
    req = urllib.request.Request(f"http://127.0.0.1:{PANEL}{path}",
                                 data=urllib.parse.urlencode(data).encode())
    return urllib.request.urlopen(req, timeout=10).status

async def echo_server():
    async def h(r, w):
        while (d := await r.read(4096)):
            w.write(d); await w.drain()
        w.close()
    srv = await asyncio.start_server(h, "127.0.0.1", ECHO)
    async with srv:
        await srv.serve_forever()

async def main():
    env = dict(os.environ, TUNNEL_SECRET=SECRET, TUNNEL_PORT=str(TUN), PYTHONPATH=ROOT)
    echo = asyncio.create_task(echo_server())
    srv = subprocess.Popen([sys.executable, f"{ROOT}/core/server.py"], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert up(TUN), "tunnel server did not start"
    pnl = subprocess.Popen([sys.executable, "-m", "uvicorn", "panel.main:app",
                            "--port", str(PANEL), "--log-level", "error"],
                           cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert up(PANEL), "panel did not start"

    status = post("/add_node", {"name": "local-test", "ip": "127.0.0.1", "country": "Turkey",
                                "secret": SECRET, "dest": f"127.0.0.1:{ECHO}"})
    print("add_node ->", status)
    body = urllib.request.urlopen(f"http://127.0.0.1:{PANEL}/", timeout=10).read().decode()
    assert "local-test" in body, "node not shown in panel"
    print("node visible in dashboard: yes")

    status = post("/connect/1", {})
    print("connect ->", status)
    assert up(10801, timeout=20), "tunnel client listener 10801 did not come up"
    print("tunnel client listening on :10801")

    r, w = await asyncio.open_connection("127.0.0.1", 10801)
    payload = b"PANEL-E2E-" + os.urandom(8).hex().encode()
    w.write(payload); await w.drain()
    got = await asyncio.wait_for(r.read(len(payload)), timeout=10)
    assert got == payload, f"mismatch sent={payload!r} got={got!r}"
    print(f"PASS: {len(payload)} bytes relayed panel-node -> foreign -> echo -> back")
    w.close()

    status = post("/disconnect/1", {})
    print("disconnect ->", status)
    time.sleep(2)
    with socket.socket() as s:
        s.settimeout(1)
        assert s.connect_ex(("127.0.0.1", 10801)) != 0, "listener still open after disconnect"
    print("PASS: tunnel torn down")

    pnl.terminate(); srv.terminate(); echo.cancel()

asyncio.run(main())
