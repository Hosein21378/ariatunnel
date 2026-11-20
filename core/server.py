#!/usr/bin/env python3
"""
AriaTunnel Server Core (Foreign VPS)
High-performance asynchronous TCP/UDP multiplexing tunnel relay.
"""
import asyncio
import logging
import sys
import os
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AriaTunnelServer")

SECRET_KEY = os.getenv("TUNNEL_SECRET", "AriaTunnelSecureKey2026!").encode()
# Ensure 32 bytes key for ChaCha20Poly1305
KEY = (SECRET_KEY * (32 // len(SECRET_KEY) + 1))[:32]
cipher = ChaCha20Poly1305(KEY)

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info('peername')
    logger.info(f"New connection from {peer}")
    try:
        # Read target destination header (e.g. host:port)
        header_len_bytes = await reader.readexactly(2)
        header_len = int.from_bytes(header_len_bytes, 'big')
        encrypted_header = await reader.readexactly(header_len)
        
        # In production, decrypt nonce + ciphertext. For boilerplate, we handle securely.
        # Format: nonce(12) + ciphertext
        nonce = encrypted_header[:12]
        ciphertext = encrypted_header[12:]
        header_plain = cipher.decrypt(nonce, ciphertext, None).decode()
        
        host, port_str = header_plain.rsplit(":", 1)
        port = int(port_str)
        logger.info(f"Connecting to target {host}:{port} for {peer}")
        
        # Connect to destination
        remote_reader, remote_writer = await asyncio.open_connection(host, port)
        writer.write(b"\x01") # OK
        await writer.drain()
        
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
            forward(reader, remote_writer),
            forward(remote_reader, writer)
        )
    except Exception as e:
        logger.error(f"Error handling connection from {peer}: {e}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        logger.info(f"Connection closed for {peer}")

async def main():
    port = int(os.getenv("TUNNEL_PORT", 8443))
    server = await asyncio.start_server(handle_client, "0.0.0.0", port)
    logger.info(f"AriaTunnel Server started on 0.0.0.0:{port}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
