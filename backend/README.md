# Room Monitor Backend

FastAPI backend for room environment readings uploaded by the Raspberry Pi.

## Local setup

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

The default SQLite database is `data/room_monitor.sqlite3`. Override it with:

```bash
ROOM_MONITOR_DB=/path/to/room_monitor.sqlite3 uvicorn app:app --host 0.0.0.0 --port 8000
```

Set API keys before using any `/api/*` endpoint:

```bash
ROOM_MONITOR_WRITE_API_KEY='change-this-write-secret' \
ROOM_MONITOR_READ_API_KEY='change-this-read-secret' \
uvicorn app:app --host 0.0.0.0 --port 8000
```

Optional abuse controls:

```bash
ROOM_MONITOR_MAX_BODY_BYTES=4096
ROOM_MONITOR_RATE_LIMIT_REQUESTS=30
ROOM_MONITOR_RATE_LIMIT_WINDOW_SECONDS=60
ROOM_MONITOR_RETENTION_DAYS=30
```

## Smoke test

```bash
curl -X POST http://127.0.0.1:8000/api/readings \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-this-write-secret' \
  -d '{"temperature_c_x100":2642,"humidity_rh_x100":6130,"pressure_pa":100820,"gas_ohm":170000,"gas_valid":1,"heat_stable":1}'

curl -H 'X-API-Key: change-this-read-secret' http://127.0.0.1:8000/api/readings/latest
curl -H 'X-API-Key: change-this-read-secret' 'http://127.0.0.1:8000/api/readings?hours=24'
```

## Raspberry Pi upload

Once the backend is reachable from the Raspberry Pi:

```bash
python3 serial_collector.py \
  --port /dev/serial0 \
  --baud 115200 \
  --db data/room_readings.sqlite3 \
  --upload-url https://SERVER_IP_OR_DOMAIN/api/readings
```

For GCP e2-micro, run this behind a firewall rule or reverse proxy. Set
`ROOM_MONITOR_WRITE_API_KEY` and `ROOM_MONITOR_READ_API_KEY`, then use HTTPS
before exposing `/api/*` publicly.
