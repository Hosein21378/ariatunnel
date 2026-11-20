#!/usr/bin/env python3
"""
AriaTunnel Client Core (Iran VPS / Entry)
Local tunnel entrypoint forwarding user traffic securely to Foreign Server.
Supports tcp (raw) and tls (TLS-wrapped, looks like HTTPS to DPI) transports.
"""
import asyncio
import logging
import os
import ssl
import sys
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AriaTunnelClient")

SECRET_KEY = os.getenv("TUNNEL_SECRET", "AriaTunnelSecureKey2026!").encode()
KEY = (SECRET_KEY * (32 // len(SECRET_KEY) + 1))[:32]
cipher = ChaCha20Poly1305(KEY)

SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8443"))
LOCAL_PORT = int(os.getenv("LOCAL_PORT", "1080"))
TARGET_DEST = os.getenv("TARGET_DEST", "1.1.1.1:443")
TRANSPORT = os.getenv("TUNNEL_TRANSPORT", "tcp")  # tcp or tls


def get_ssl_context():
    """Client-side SSL context for TLS transport (accepts self-signed cert)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def handle_local(local_reader: asyncio.StreamReader, local_writer: asyncio.StreamWriter):
    peer = local_writer.get_extra_info("peername")
    try:
        # Connect to foreign server tunnel
        if TRANSPORT == "tls":
            ssl_context = get_ssl_context()
            remote_reader, remote_writer = await asyncio.open_connection(
                SERVER_HOST, SERVER_PORT, ssl=ssl_context
            )
        else:
            remote_reader, remote_writer = await asyncio.open_connection(SERVER_HOST, SERVER_PORT)

        # Send encrypted header with target destination
        nonce = os.urandom(12)
        header = nonce + cipher.encrypt(nonce, TARGET_DEST.encode(), None)
        remote_writer.write(len(header).to_bytes(2, "big") + header)
        await remote_writer.drain()

        # Wait for handshake response
        status = await remote_reader.readexactly(1)
        if status != b"\x01":
            logger.error("Tunnel handshake failed at remote server")
            return

        async def forward(src, dst):
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        await asyncio.gather(
            forward(local_reader, remote_writer),
            forward(remote_reader, local_writer),
        )
    except Exception as e:
        logger.error(f"Client tunnel error: {e}")
    finally:
        local_writer.close()
        try:
            await local_writer.wait_closed()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle_local, "0.0.0.0", LOCAL_PORT)
    transport_label = "TLS (DPI-resistant)" if TRANSPORT == "tls" else "TCP"
    logger.info(
        f"AriaTunnel Client ({transport_label}) on 0.0.0.0:{LOCAL_PORT} -> {SERVER_HOST}:{SERVER_PORT} -> {TARGET_DEST}"
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped.")
