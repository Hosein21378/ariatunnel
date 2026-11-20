#!/usr/bin/env python3
"""Self-check: end-to-end data relay through AriaTunnel server+client."""
import asyncio, os, sys, subprocess, time, socket

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECHO_PORT, TUN_PORT, LOCAL_PORT = 19999, 18443, 11080

async def echo_server():
    async def h(r, w):
        while (d := await r.read(4096)):
            w.write(d); await w.drain()
        w.close()
    s = await asyncio.start_server(h, "127.0.0.1", ECHO_PORT)
    async with s:
        await s.serve_forever()

def wait_port(port, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.15)
    return False

async def main():
    env = dict(os.environ, TUNNEL_SECRET="test-secret-123", TUNNEL_PORT=str(TUN_PORT),
               SERVER_HOST="127.0.0.1", SERVER_PORT=str(TUN_PORT), LOCAL_PORT=str(LOCAL_PORT),
               TARGET_DEST=f"127.0.0.1:{ECHO_PORT}")
    echo = asyncio.create_task(echo_server())
    srv = subprocess.Popen([sys.executable, f"{ROOT}/core/server.py"], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert wait_port(TUN_PORT), "tunnel server did not listen"
    cli = subprocess.Popen([sys.executable, f"{ROOT}/core/client.py"], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert wait_port(LOCAL_PORT), "tunnel client did not listen"
    try:
        r, w = await asyncio.open_connection("127.0.0.1", LOCAL_PORT)
        payload = b"ARIA-TUNNEL-E2E-" + os.urandom(8).hex().encode()
        w.write(payload); await w.drain()
        got = await asyncio.wait_for(r.read(len(payload)), timeout=8)
        assert got == payload, f"payload mismatch: sent={payload!r} got={got!r}"
        print("PASS: data relayed end-to-end", len(payload), "bytes")
        w.close()
    finally:
        cli.terminate(); srv.terminate(); echo.cancel()

asyncio.run(main())
