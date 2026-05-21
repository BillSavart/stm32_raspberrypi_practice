#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/stm32_raspberrypi_practice}"
SERVICE_USER="${SERVICE_USER:-pi}"
SERVICE_GROUP="${SERVICE_GROUP:-pi}"
ENV_DIR="/etc/room-monitor"
ENV_FILE="${ENV_DIR}/firebase_collector.env"
SERVICE_FILE="/etc/systemd/system/room-monitor-firebase-collector.service"
DEFAULT_PYTHON_BIN="${REPO_DIR}/raspberry_pi/.venv/bin/python"
PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_PYTHON_BIN}}"

if [[ ! -d "${REPO_DIR}/raspberry_pi" ]]; then
  echo "Collector directory not found: ${REPO_DIR}/raspberry_pi" >&2
  echo "Set REPO_DIR=/path/to/stm32_raspberrypi_practice if your repo is elsewhere." >&2
  exit 1
fi

sudo mkdir -p "${ENV_DIR}"
if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  echo "Service user does not exist: ${SERVICE_USER}" >&2
  echo "Set SERVICE_USER to an existing user if your Raspberry Pi account is not pi." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  sudo cp "${REPO_DIR}/deploy/env/firebase_collector.env.example" "${ENV_FILE}"
  sudo chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Edit Firebase settings before starting long-term."
fi

if [[ "${PYTHON_BIN}" == "${DEFAULT_PYTHON_BIN}" ]]; then
  python3 -m venv "${REPO_DIR}/raspberry_pi/.venv"
  "${PYTHON_BIN}" -m pip install --upgrade pip
  "${PYTHON_BIN}" -m pip install -r "${REPO_DIR}/raspberry_pi/requirements.txt"
else
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "PYTHON_BIN is not executable: ${PYTHON_BIN}" >&2
    exit 1
  fi
  sudo -u "${SERVICE_USER}" "${PYTHON_BIN}" -m pip install -r "${REPO_DIR}/raspberry_pi/requirements.txt"
fi

sudo mkdir -p "${REPO_DIR}/raspberry_pi/data"
sudo chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${REPO_DIR}/raspberry_pi/data"
sudo cp "${REPO_DIR}/deploy/systemd/room-monitor-firebase-collector.service" "${SERVICE_FILE}"
sudo sed -i "s#User=pi#User=${SERVICE_USER}#g" "${SERVICE_FILE}"
sudo sed -i "s#Group=pi#Group=${SERVICE_GROUP}#g" "${SERVICE_FILE}"
sudo sed -i "s#/usr/bin/python3#${PYTHON_BIN}#g" "${SERVICE_FILE}"
sudo sed -i "s#/opt/stm32_raspberrypi_practice#${REPO_DIR}#g" "${SERVICE_FILE}"

sudo systemctl daemon-reload
sudo systemctl enable room-monitor-firebase-collector.service
sudo systemctl restart room-monitor-firebase-collector.service
sudo systemctl status room-monitor-firebase-collector.service --no-pager
