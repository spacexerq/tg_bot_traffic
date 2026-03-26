#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/traffic-guard}"
ENV_TARGET="${ENV_TARGET:-/etc/traffic-guard-control.env}"
SERVERS_TARGET="${SERVERS_TARGET:-/etc/traffic-guard/control-servers.json}"
STATE_DIR="${STATE_DIR:-/var/lib/traffic-guard}"
SERVICE_NAME="${SERVICE_NAME:-traffic-guard-control-bot}"
SYSTEMD_UNIT_TARGET="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemd is required." >&2
  exit 1
fi

mkdir -p "${APP_DIR}" "${STATE_DIR}" "$(dirname "${ENV_TARGET}")" "$(dirname "${SERVERS_TARGET}")"

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install "${PWD}"

cat > "${SYSTEMD_UNIT_TARGET}" <<EOF
[Unit]
Description=Traffic Guard control bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_TARGET}
ExecStart=${APP_DIR}/.venv/bin/traffic-guard --env-file ${ENV_TARGET} control-bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

if [[ ! -f "${ENV_TARGET}" ]]; then
  install -m 0600 "${PWD}/deploy/control-bot.env.example" "${ENV_TARGET}"
  echo "Created ${ENV_TARGET}"
else
  echo "Keeping existing ${ENV_TARGET}"
fi

if [[ ! -f "${SERVERS_TARGET}" ]]; then
  install -m 0600 "${PWD}/deploy/control-servers.example.json" "${SERVERS_TARGET}"
  echo "Created ${SERVERS_TARGET}"
else
  echo "Keeping existing ${SERVERS_TARGET}"
fi

chmod 700 "${STATE_DIR}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo "Control bot installation completed."
echo "Next steps:"
echo "1. Edit ${ENV_TARGET}"
echo "2. Edit ${SERVERS_TARGET}"
echo "3. Run: systemctl start ${SERVICE_NAME}"
echo "4. Check: systemctl status ${SERVICE_NAME}"
