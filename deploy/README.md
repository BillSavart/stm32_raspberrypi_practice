# Deployment

This folder contains deployment helpers for the room monitor prototype.

## Backend on GCP e2-micro

Assumptions:

- Ubuntu VM
- Repo located at `/opt/stm32_raspberrypi_practice`
- Backend listens on `127.0.0.1:8000`; Nginx exposes HTTPS.

On the VM:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv sqlite3

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
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:8000/api/readings/latest
```

Set strong `ROOM_MONITOR_WRITE_API_KEY` and `ROOM_MONITOR_READ_API_KEY` values in
`/etc/room-monitor/backend.env`. The write key is for the Raspberry Pi; the read
key is for querying data and the future LINE Bot.

### HTTPS reverse proxy

For public access, keep uvicorn bound behind Nginx and expose only ports `80`
and `443` in the GCP firewall.

```bash
DOMAIN=your.domain.example sudo -E bash deploy/install_nginx_https.sh
```

The included Nginx config limits `/api/` traffic and caps request bodies at 4 KB.
The FastAPI app also has a small built-in rate limiter controlled by
`ROOM_MONITOR_RATE_LIMIT_REQUESTS`, `ROOM_MONITOR_RATE_LIMIT_WINDOW_SECONDS`,
and `ROOM_MONITOR_MAX_BODY_BYTES`.

### Retention and backups

Backend readings older than `ROOM_MONITOR_RETENTION_DAYS` are pruned during
inserts. Set it to `0` to disable pruning.

`install_backend_service.sh` also installs `room-monitor-backup.timer`, which
creates a daily compressed SQLite backup in `ROOM_MONITOR_BACKUP_DIR` and keeps
only `ROOM_MONITOR_BACKUP_RETENTION_DAYS`.

Check backups:

```bash
systemctl list-timers room-monitor-backup.timer
journalctl -u room-monitor-backup.service --no-pager
ls -lh /opt/stm32_raspberrypi_practice/backend/backups
```

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

The backend and collector services use systemd restart limits. If a bad config
causes repeated failures, fix the config and run:

```bash
sudo systemctl reset-failed room-monitor-backend.service
sudo systemctl reset-failed room-monitor-collector.service
```

To reduce GCP traffic and Pi work, tune:

```text
UPLOAD_EVERY_SECONDS=60
```

in `/etc/room-monitor/collector.env`. The collector keeps local SQLite records
for every accepted reading, but only attempts backend upload at that interval.

To reduce local storage use, tune:

```text
LOCAL_RETENTION_DAYS=30
LOCAL_PRUNE_EVERY_SECONDS=3600
```

If you use GPIO UART instead of Nucleo USB serial, set:

```text
SERIAL_PORT=/dev/serial0
```

in `/etc/room-monitor/collector.env`.
