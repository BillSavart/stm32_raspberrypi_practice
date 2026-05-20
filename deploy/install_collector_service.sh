#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/stm32_raspberrypi_practice}"
SERVICE_USER="${SERVICE_USER:-pi}"
SERVICE_GROUP="${SERVICE_GROUP:-pi}"
ENV_DIR="/etc/room-monitor"
ENV_FILE="${ENV_DIR}/collector.env"
SERVICE_FILE="/etc/systemd/system/room-monitor-collector.service"

if [[ ! -d "${REPO_DIR}/raspberry_pi" ]]; then
  echo "Collector directory not found: ${REPO_DIR}/raspberry_pi" >&2
  echo "Set REPO_DIR=/path/to/stm32_raspberrypi_practice if your repo is elsewhere." >&2
  exit 1
fi

sudo mkdir -p "${ENV_DIR}"
if [[ ! -f "${ENV_FILE}" ]]; then
  sudo cp "${REPO_DIR}/deploy/env/collector.env.example" "${ENV_FILE}"
  sudo chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Edit SERIAL_PORT, UPLOAD_URL, and ROOM_MONITOR_API_KEY before starting long-term."
fi

python3 -m venv "${REPO_DIR}/raspberry_pi/.venv"
"${REPO_DIR}/raspberry_pi/.venv/bin/python" -m pip install --upgrade pip
"${REPO_DIR}/raspberry_pi/.venv/bin/python" -m pip install -r "${REPO_DIR}/raspberry_pi/requirements.txt"

sudo chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${REPO_DIR}/raspberry_pi"
sudo cp "${REPO_DIR}/deploy/systemd/room-monitor-collector.service" "${SERVICE_FILE}"
sudo sed -i "s#User=pi#User=${SERVICE_USER}#g" "${SERVICE_FILE}"
sudo sed -i "s#Group=pi#Group=${SERVICE_GROUP}#g" "${SERVICE_FILE}"
sudo sed -i "s#/opt/stm32_raspberrypi_practice#${REPO_DIR}#g" "${SERVICE_FILE}"

sudo systemctl daemon-reload
sudo systemctl enable room-monitor-collector.service
sudo systemctl restart room-monitor-collector.service
sudo systemctl status room-monitor-collector.service --no-pager
