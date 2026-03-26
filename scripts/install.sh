#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/traffic-guard}"
ENV_TARGET="${ENV_TARGET:-/etc/traffic-guard.env}"
STATE_DIR="${STATE_DIR:-/var/lib/traffic-guard}"
SERVICE_NAME="${SERVICE_NAME:-traffic-guard}"
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

mkdir -p "${APP_DIR}" "${STATE_DIR}"
mkdir -p "$(dirname "${ENV_TARGET}")"

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install "${PWD}"

cat > "${SYSTEMD_UNIT_TARGET}" <<EOF
[Unit]
Description=Traffic Guard Telegram notifier
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_TARGET}
ExecStart=${APP_DIR}/.venv/bin/traffic-guard daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

if [[ ! -f "${ENV_TARGET}" ]]; then
  install -m 0600 "${PWD}/deploy/traffic-guard.env.example" "${ENV_TARGET}"
  echo "Created ${ENV_TARGET}. Fill it before starting the service."
else
  echo "Keeping existing ${ENV_TARGET}."
fi

chmod 700 "${STATE_DIR}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo "Installation completed."
echo "Next steps:"
echo "1. Edit ${ENV_TARGET}"
echo "2. Run: systemctl start ${SERVICE_NAME}"
echo "3. Check: systemctl status ${SERVICE_NAME}"
