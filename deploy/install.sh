#!/usr/bin/env bash
# AriaTunnel one-line installer
# Usage: bash install.sh [server|client|panel]
set -euo pipefail

ROLE="${1:-panel}"
REPO="${REPO:-https://github.com/USER/ariatunnel}"

echo "==> AriaTunnel installer (role: $ROLE)"

command -v python3 >/dev/null || { echo "python3 required"; exit 1; }
command -v pip3 >/dev/null || { echo "pip3 required"; exit 1; }

if [ ! -d "ariatunnel" ]; then
  command -v git >/dev/null || { echo "git required"; exit 1; }
  git clone "$REPO" ariatunnel
fi
cd ariatunnel
pip3 install --quiet -r requirements.txt

SECRET_FILE=/etc/ariatunnel.secret
if [ ! -f "$SECRET_FILE" ]; then
  openssl rand -hex 32 > "$SECRET_FILE"; chmod 600 "$SECRET_FILE"
  echo "==> generated secret at $SECRET_FILE — copy this file to the other node"
fi
export TUNNEL_SECRET="$(cat "$SECRET_FILE")"

case "$ROLE" in
  server)
    cat >/etc/systemd/system/ariatunnel-server.service <<EOF
[Unit]
Description=AriaTunnel Server
After=network-online.target
[Service]
Environment=TUNNEL_SECRET=$(cat "$SECRET_FILE")
Environment=TUNNEL_PORT=8443
ExecStart=/usr/bin/python3 $(pwd)/core/server.py
Restart=always
[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload && systemctl enable --now ariatunnel-server
    echo "==> server running on :8443"
    ;;
  client)
    echo "SERVER_HOST is required: SERVER_HOST=1.2.3.4 bash install.sh client"
    cat >/etc/systemd/system/ariatunnel-client.service <<EOF
[Unit]
Description=AriaTunnel Client
After=network-online.target
[Service]
Environment=TUNNEL_SECRET=$(cat "$SECRET_FILE")
Environment=SERVER_HOST=${SERVER_HOST:?set SERVER_HOST}
Environment=SERVER_PORT=8443
Environment=LOCAL_PORT=1080
ExecStart=/usr/bin/python3 $(pwd)/core/client.py
Restart=always
[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload && systemctl enable --now ariatunnel-client
    echo "==> client listening on :1080"
    ;;
  panel)
    cat >/etc/systemd/system/ariatunnel-panel.service <<EOF
[Unit]
Description=AriaTunnel Panel
After=network-online.target
[Service]
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 panel/main.py
Restart=always
[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload && systemctl enable --now ariatunnel-panel
    echo "==> panel on :8000"
    ;;
esac
