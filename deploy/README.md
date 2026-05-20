# Deployment

This folder contains deployment helpers for the room monitor prototype.

## Backend on GCP e2-micro

Assumptions:

- Ubuntu VM
- Repo located at `/opt/stm32_raspberrypi_practice`
- Backend listens on port `8000`

On the VM:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv

sudo mkdir -p /opt
sudo git clone YOUR_REPO_URL /opt/stm32_raspberrypi_practice
cd /opt/stm32_raspberrypi_practice

sudo bash deploy/install_backend_service.sh
sudo nano /etc/room-monitor/backend.env
sudo systemctl restart room-monitor-backend.service
```

Check:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/readings/latest
```

If GCP firewall exposes port `8000`, set a strong `ROOM_MONITOR_API_KEY` in
`/etc/room-monitor/backend.env`.

## Raspberry Pi collector service

Assumptions:

- Repo located at `/opt/stm32_raspberrypi_practice`
- Nucleo USB serial appears as `/dev/ttyACM0`

On the Raspberry Pi:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv

sudo mkdir -p /opt
sudo git clone YOUR_REPO_URL /opt/stm32_raspberrypi_practice
cd /opt/stm32_raspberrypi_practice

sudo bash deploy/install_collector_service.sh
sudo nano /etc/room-monitor/collector.env
sudo systemctl restart room-monitor-collector.service
```

Check logs:

```bash
journalctl -u room-monitor-collector.service -f
```

To reduce GCP traffic and Pi work, tune:

```text
UPLOAD_EVERY_SECONDS=60
```

in `/etc/room-monitor/collector.env`. The collector keeps local SQLite records
for every accepted reading, but only attempts backend upload at that interval.

If you use GPIO UART instead of Nucleo USB serial, set:

```text
SERIAL_PORT=/dev/serial0
```

in `/etc/room-monitor/collector.env`.
