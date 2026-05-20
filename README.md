# stm32_raspberrypi_practice

## RoomTemperatureDetector

STM32F446RE + BME680 room environment monitor prototype.

### Current STM32 wiring

The current firmware uses `SPI1` for the BME680 and `USART2` for serial logs.

| STM32F446RE | BME680 |
| --- | --- |
| `3.3V` | `VIN` / `3V3` |
| `GND` | `GND` |
| `PA5` | `SCK` |
| `PA6` | `SDO` / `MISO` |
| `PA7` | `SDI` / `MOSI` |
| `PB6` | `CS` |

Serial monitor:

- Port: ST-LINK Virtual COM Port
- Baud rate: `115200`
- Format: `8N1`

### Output format

The board prints one JSON line about every 2 seconds:

```json
{"temperature_c_x100":2642,"humidity_rh_x100":6130,"pressure_pa":100820,"gas_ohm":82345,"gas_valid":1,"heat_stable":1}
```

Field meaning:

- `temperature_c_x100`: Celsius multiplied by 100. `2642` means `26.42 C`.
- `humidity_rh_x100`: relative humidity multiplied by 100. `6130` means `61.30%`.
- `pressure_pa`: pressure in pascals.
- `gas_ohm`: gas sensor resistance in ohms.
- `gas_valid`: `1` means the gas reading is valid.
- `heat_stable`: `1` means the gas heater reached a stable state.

This JSON-line format is intentionally Raspberry Pi friendly: the Pi can read
each UART line, parse it as JSON, add a timestamp, and forward it to the GCP
backend later.

## Raspberry Pi collector

The Raspberry Pi side lives in `raspberry_pi/`.

It reads STM32 JSON lines from UART, validates the expected fields, adds a UTC
timestamp, and stores readings in SQLite.

Quick development test without hardware:

```bash
cd raspberry_pi
printf '%s\n' '{"temperature_c_x100":2642,"humidity_rh_x100":6130,"pressure_pa":100820,"gas_ohm":82345,"gas_valid":1,"heat_stable":1}' \
  | python3 serial_collector.py --stdin --db /tmp/room_readings.sqlite3
```

Run on Raspberry Pi:

```bash
cd raspberry_pi
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 serial_collector.py --port /dev/serial0 --baud 115200 --db data/room_readings.sqlite3
```

Detailed Pi wiring and setup notes are in `raspberry_pi/README.md`.

## Backend API

The backend lives in `backend/`. It exposes:

- `POST /api/readings`
- `GET /api/readings/latest`
- `GET /api/readings?hours=24`
- `GET /health`

Run locally:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then run the Pi collector with upload enabled:

```bash
cd raspberry_pi
python3 serial_collector.py \
  --port /dev/serial0 \
  --baud 115200 \
  --db data/room_readings.sqlite3 \
  --upload-url https://SERVER_IP_OR_DOMAIN/api/readings \
  --upload-every-seconds 60
```

For deployment, use separate write/read API keys:

- `ROOM_MONITOR_WRITE_API_KEY`: Raspberry Pi uploads
- `ROOM_MONITOR_READ_API_KEY`: queries and future LINE Bot

Copy `.env.example` to `.env` for local development secrets. `.env` is ignored
by git; do not commit real API keys.
