#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: sudo bash scripts/install-profile.sh <profile-name>" >&2
  exit 1
fi

PROFILE_NAME="$1"
APP_DIR="${APP_DIR:-/opt/traffic-guard}"
PROFILE_DIR="${PROFILE_DIR:-/etc/traffic-guard}"
PROFILE_ENV_TARGET="${PROFILE_DIR}/${PROFILE_NAME}.env"
TEMPLATE_UNIT_TARGET="/etc/systemd/system/traffic-guard@.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

mkdir -p "${PROFILE_DIR}" "/var/lib/traffic-guard/${PROFILE_NAME}"
chmod 700 "/var/lib/traffic-guard/${PROFILE_NAME}"

if [[ ! -x "${APP_DIR}/.venv/bin/traffic-guard" ]]; then
  echo "Base installation not found in ${APP_DIR}. Run scripts/install.sh first." >&2
  exit 1
fi

if [[ ! -f "${TEMPLATE_UNIT_TARGET}" ]]; then
  echo "Template unit ${TEMPLATE_UNIT_TARGET} not found. Run scripts/install.sh first." >&2
  exit 1
fi

if [[ ! -f "${PROFILE_ENV_TARGET}" ]]; then
  install -m 0600 "${PWD}/deploy/traffic-guard.env.example" "${PROFILE_ENV_TARGET}"
  {
    echo ""
    echo "# Profile-specific defaults"
    echo "TG_SERVER_NAME=${PROFILE_NAME}"
    echo "TG_STATE_FILE=/var/lib/traffic-guard/${PROFILE_NAME}/state.json"
  } >> "${PROFILE_ENV_TARGET}"
  echo "Created ${PROFILE_ENV_TARGET}"
else
  echo "Keeping existing ${PROFILE_ENV_TARGET}"
fi

systemctl daemon-reload
systemctl enable "traffic-guard@${PROFILE_NAME}"

echo "Profile installation completed."
echo "Next steps:"
echo "1. Edit ${PROFILE_ENV_TARGET}"
echo "2. Run: systemctl start traffic-guard@${PROFILE_NAME}"
echo "3. Check: systemctl status traffic-guard@${PROFILE_NAME}"
