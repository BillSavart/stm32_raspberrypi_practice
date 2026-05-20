#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${DOMAIN:?Set DOMAIN=your.domain.example}"
REPO_DIR="${REPO_DIR:-/opt/stm32_raspberrypi_practice}"
NGINX_SITE="/etc/nginx/sites-available/room-monitor.conf"

if [[ ! -f "${REPO_DIR}/deploy/nginx/room-monitor.conf" ]]; then
  echo "Nginx template not found: ${REPO_DIR}/deploy/nginx/room-monitor.conf" >&2
  exit 1
fi

sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

sudo cp "${REPO_DIR}/deploy/nginx/room-monitor.conf" "${NGINX_SITE}"
sudo sed -i "s/YOUR_DOMAIN/${DOMAIN}/g" "${NGINX_SITE}"
sudo ln -sf "${NGINX_SITE}" /etc/nginx/sites-enabled/room-monitor.conf
sudo nginx -t
sudo certbot --nginx -d "${DOMAIN}"
sudo nginx -t
sudo systemctl reload nginx
