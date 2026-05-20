#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/stm32_raspberrypi_practice}"
SERVICE_USER="${SERVICE_USER:-roommonitor}"
SERVICE_GROUP="${SERVICE_GROUP:-roommonitor}"
ENV_DIR="/etc/room-monitor"
ENV_FILE="${ENV_DIR}/backend.env"
SERVICE_FILE="/etc/systemd/system/room-monitor-backend.service"

if [[ ! -d "${REPO_DIR}/backend" ]]; then
  echo "Backend directory not found: ${REPO_DIR}/backend" >&2
  echo "Set REPO_DIR=/path/to/stm32_raspberrypi_practice if your repo is elsewhere." >&2
  exit 1
fi

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  sudo useradd --system --home "${REPO_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

sudo mkdir -p "${ENV_DIR}"
if [[ ! -f "${ENV_FILE}" ]]; then
  sudo cp "${REPO_DIR}/deploy/env/backend.env.example" "${ENV_FILE}"
  sudo chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Edit ROOM_MONITOR_WRITE_API_KEY and ROOM_MONITOR_READ_API_KEY before exposing the service."
fi

python3 -m venv "${REPO_DIR}/backend/.venv"
"${REPO_DIR}/backend/.venv/bin/python" -m pip install --upgrade pip
"${REPO_DIR}/backend/.venv/bin/python" -m pip install -r "${REPO_DIR}/backend/requirements.txt"

sudo mkdir -p "${REPO_DIR}/backend/data"
sudo mkdir -p "${REPO_DIR}/backend/backups"
sudo chown -R root:root "${REPO_DIR}/backend"
sudo chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${REPO_DIR}/backend/data"
sudo chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${REPO_DIR}/backend/backups"
sudo cp "${REPO_DIR}/deploy/systemd/room-monitor-backend.service" "${SERVICE_FILE}"
sudo cp "${REPO_DIR}/deploy/systemd/room-monitor-backup.service" /etc/systemd/system/room-monitor-backup.service
sudo cp "${REPO_DIR}/deploy/systemd/room-monitor-backup.timer" /etc/systemd/system/room-monitor-backup.timer
sudo sed -i "s#User=roommonitor#User=${SERVICE_USER}#g" "${SERVICE_FILE}"
sudo sed -i "s#Group=roommonitor#Group=${SERVICE_GROUP}#g" "${SERVICE_FILE}"
sudo sed -i "s#/opt/stm32_raspberrypi_practice#${REPO_DIR}#g" "${SERVICE_FILE}"
sudo sed -i "s#User=roommonitor#User=${SERVICE_USER}#g" /etc/systemd/system/room-monitor-backup.service
sudo sed -i "s#Group=roommonitor#Group=${SERVICE_GROUP}#g" /etc/systemd/system/room-monitor-backup.service
sudo sed -i "s#/opt/stm32_raspberrypi_practice#${REPO_DIR}#g" /etc/systemd/system/room-monitor-backup.service

sudo systemctl daemon-reload
sudo systemctl enable room-monitor-backend.service
sudo systemctl enable room-monitor-backup.timer
sudo systemctl restart room-monitor-backend.service
sudo systemctl restart room-monitor-backup.timer
sudo systemctl status room-monitor-backend.service --no-pager
