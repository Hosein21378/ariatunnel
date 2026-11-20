#!/usr/bin/env bash
# AriaTunnel one-line installer
#   server : panel host / foreign node  -> bash <(curl -sSL .../install.sh) server
#   client : iran node                  -> SERVER_HOST=1.2.3.4 bash <(curl -sSL .../install.sh) client
#   panel  : management dashboard       -> bash <(curl -sSL .../install.sh) panel
set -euo pipefail

ROLE="${1:-panel}"
REPO="${REPO:-https://github.com/Hosein21378/ariatunnel}"
DIR=/opt/ariatunnel
SECRET_FILE=/etc/ariatunnel.secret

echo "==> AriaTunnel installer (role: $ROLE)"

command -v python3 >/dev/null || { apt-get update -qq && apt-get install -y -qq python3 python3-pip; }
command -v curl >/dev/null || apt-get install -y -qq curl

# --- fetch code (tarball, works without git) ---------------------------------
if [ ! -d "$DIR" ]; then
  mkdir -p "$DIR"
  curl -sSL "https://github.com/Hosein21378/ariatunnel/archive/refs/heads/master.tar.gz" \
    | tar xz -C "$DIR" --strip-components=1
fi
cd "$DIR"

# --- deps --------------------------------------------------------------------
python3 -m pip install --quiet --break-system-packages -r requirements.txt 2>/dev/null \
  || python3 -m pip install --quiet -r requirements.txt

# --- shared secret -----------------------------------------------------------
if [ ! -f "$SECRET_FILE" ]; then
  python3 -c "import secrets;print(secrets.token_hex(32))" > "$SECRET_FILE"
  chmod 600 "$SECRET_FILE"
fi
SECRET="$(cat "$SECRET_FILE")"

unit() {
  cat >"/etc/systemd/system/ariatunnel-$1.service"
  systemctl daemon-reload
  systemctl enable --now "ariatunnel-$1"
}

case "$ROLE" in
  server)
    unit server <<EOF
[Unit]
Description=AriaTunnel Server
After=network-online.target
[Service]
Environment=TUNNEL_SECRET=$SECRET
Environment=TUNNEL_PORT=8443
ExecStart=/usr/bin/python3 $DIR/core/server.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
    echo
    echo "================ SAVE THIS SECRET ================"
    echo "TUNNEL_SECRET=$SECRET"
    echo "=================================================="
    echo "==> tunnel server listening on :8443"
    ;;
  client)
    : "${SERVER_HOST:?usage: SERVER_HOST=<foreign-ip> bash install.sh client}"
    unit client <<EOF
[Unit]
Description=AriaTunnel Client
After=network-online.target
[Service]
Environment=TUNNEL_SECRET=$SECRET
Environment=SERVER_HOST=$SERVER_HOST
Environment=SERVER_PORT=${SERVER_PORT:-8443}
Environment=LOCAL_PORT=${LOCAL_PORT:-1080}
Environment=TARGET_DEST=${TARGET_DEST:-1.1.1.1:443}
Environment=TUNNEL_SECRET=${SECRET_OVERRIDE:-$SECRET}
ExecStart=/usr/bin/python3 $DIR/core/client.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
    echo "==> client :${LOCAL_PORT:-1080} -> $SERVER_HOST:${SERVER_PORT:-8443}"
    ;;
  panel)
    unit panel <<EOF
[Unit]
Description=AriaTunnel Panel
After=network-online.target
[Service]
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/panel/main.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
    IP="$(curl -s --max-time 5 https://api.ipify.org || echo "<server-ip>")"
    echo
    echo "==> panel ready:  http://$IP:8000"
    echo "==> panel secret: $SECRET   (paste into node form if the node has none)"
    ;;
  *)
    echo "unknown role: $ROLE (use server|client|panel)"; exit 1
    ;;
esac
