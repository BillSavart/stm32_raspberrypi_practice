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
each UART line, parse it as JSON, add a timestamp, and upload throttled samples
to Firebase later.

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

## Firebase + GitHub Pages path

Use Firebase Realtime Database as the data store and GitHub Pages as the
phone-friendly dashboard.

```text
STM32 -> Raspberry Pi -> Firebase Realtime Database -> GitHub Pages dashboard
```

The Firebase path keeps local SQLite storage on the Pi, but uploads only one
sample per interval:

```bash
cd raspberry_pi
export FIREBASE_API_KEY=your-firebase-web-api-key
export FIREBASE_DEVICE_EMAIL=room-device@example.com
export FIREBASE_DEVICE_PASSWORD=your-device-password

python3 firebase_uploader.py \
  --port /dev/ttyACM0 \
  --baud 115200 \
  --db data/room_readings.sqlite3 \
  --firebase-database-url https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com \
  --upload-every-seconds 60
```

The static dashboard lives in `web/`. Edit `web/firebase-config.js` with the
Firebase web app config, then enable GitHub Pages with GitHub Actions as the
source. The included workflow publishes `web/`.

Firebase Realtime Database rules are in `firebase/database.rules.json`. Replace
`REPLACE_WITH_FIREBASE_DEVICE_UID` with the Firebase Auth UID for the dedicated
device account before publishing the rules.
