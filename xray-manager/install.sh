#!/usr/bin/env bash
# MIFTAH Xray Manager agent installer — run as root on the Xray server.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "run as root" >&2
  exit 1
fi

AGENT_TOKEN="${AGENT_TOKEN:-$(openssl rand -hex 32)}"
XRAY_BIN="${XRAY_BIN:-/usr/local/bin/xray}"
XRAY_CONFIG="${XRAY_CONFIG:-/usr/local/etc/xray/config.json}"

apt-get update -y
apt-get install -y python3 python3-venv python3-pip curl unzip openssl systemd

# Xray-core (official installer) if not present
if [[ ! -x "$XRAY_BIN" ]]; then
  bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
fi

install -d -m 755 /opt/miftah-xray-manager
cp agent.py requirements.txt /opt/miftah-xray-manager/
python3 -m venv /opt/miftah-xray-manager/venv
/opt/miftah-xray-manager/venv/bin/pip install --no-cache-dir -r /opt/miftah-xray-manager/requirements.txt

cat > /etc/miftah-agent.env <<ENV
AGENT_TOKEN=${AGENT_TOKEN}
XRAY_BIN=${XRAY_BIN}
XRAY_CONFIG=${XRAY_CONFIG}
XRAY_SERVICE=xray
ENV
chmod 600 /etc/miftah-agent.env

cp miftah-xray-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now miftah-xray-agent

echo
echo "Agent installed."
echo "AGENT_TOKEN=${AGENT_TOKEN}"
echo "Agent URL (local): http://127.0.0.1:8090"
echo "Expose it to the control plane through Caddy/HTTPS on a private path."
