#!/usr/bin/env python3
"""
AriaTunnel Server Core (Foreign VPS / Exit)
High-performance asynchronous TCP tunnel relay with TLS support for DPI resistance.
Entry side (Iran) connects here; we forward decrypted traffic to the real target.
"""
import asyncio
import logging
import os
import ssl
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AriaTunnelServer")

SECRET_KEY = os.getenv("TUNNEL_SECRET", "AriaTunnelSecureKey2026!").encode()
KEY = (SECRET_KEY * (32 // len(SECRET_KEY) + 1))[:32]
cipher = ChaCha20Poly1305(KEY)

TUNNEL_PORT = int(os.getenv("TUNNEL_PORT", "8443"))
TRANSPORT = os.getenv("TUNNEL_TRANSPORT", "tcp")  # tcp or tls


def generate_self_signed_cert():
    """Self-signed cert so TLS transport looks like HTTPS to DPI."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "TR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Istanbul"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Istanbul"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AriaTunnel"),
        x509.NameAttribute(NameOID.COMMON_NAME, "ariatunnel.local"),
    ])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("ariatunnel.local")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return cert_pem, key_pem


def get_ssl_context():
    cert_pem, key_pem = generate_self_signed_cert()
    cert_file = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
    cert_file.write(cert_pem)
    cert_file.close()
    key_file = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
    key_file.write(key_pem)
    key_file.close()
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(cert_file.name, key_file.name)
    os.unlink(cert_file.name)
    os.unlink(key_file.name)
    return ctx


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


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info("peername")
    logger.info(f"New tunnel connection from {peer}")
    try:
        header_len_bytes = await reader.readexactly(2)
        header_len = int.from_bytes(header_len_bytes, "big")
        encrypted_header = await reader.readexactly(header_len)

        nonce = encrypted_header[:12]
        ciphertext = encrypted_header[12:]
        header_plain = cipher.decrypt(nonce, ciphertext, None).decode()

        host, port_str = header_plain.rsplit(":", 1)
        port = int(port_str)
        logger.info(f"Forwarding {peer} -> {host}:{port}")

        remote_reader, remote_writer = await asyncio.open_connection(host, port)
        writer.write(b"\x01")  # handshake OK
        await writer.drain()

        await asyncio.gather(
            forward(reader, remote_writer),
            forward(remote_writer, writer),
        )
    except Exception as e:
        logger.error(f"Tunnel error for {peer}: {e}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        logger.info(f"Tunnel closed for {peer}")


async def main():
    if TRANSPORT == "tls":
        ssl_context = get_ssl_context()
        server = await asyncio.start_server(handle_client, "0.0.0.0", TUNNEL_PORT, ssl=ssl_context)
        logger.info(f"AriaTunnel Server (TLS/wss-like) on 0.0.0.0:{TUNNEL_PORT}")
    else:
        server = await asyncio.start_server(handle_client, "0.0.0.0", TUNNEL_PORT)
        logger.info(f"AriaTunnel Server (TCP) on 0.0.0.0:{TUNNEL_PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
