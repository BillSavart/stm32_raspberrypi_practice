# Raspberry Pi collector

This folder contains the Raspberry Pi side of the room monitor prototype. It
reads JSON lines from the STM32 UART and stores validated readings in SQLite.

## Hardware wiring

Use 3.3 V UART only.

| STM32F446RE | Raspberry Pi 5 |
| --- | --- |
| `USART2 TX` / `PA2` | `GPIO15` / `RXD0` / physical pin 10 |
| `GND` | `GND` |

For this one-way collector, STM32 `RX` is not required yet.

## Raspberry Pi setup

Enable the serial port on Raspberry Pi OS:

```bash
sudo raspi-config
```

Choose:

```text
Interface Options -> Serial Port
Login shell over serial: No
Serial port hardware: Yes
```

Then reboot:

```bash
sudo reboot
```

Install Python dependency:

```bash
cd ~/stm32_raspberrypi_practice/raspberry_pi
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Run

```bash
python3 serial_collector.py --port /dev/serial0 --baud 115200 --db data/room_readings.sqlite3
```

If your STM32 is connected through a USB serial adapter instead, the port may be
similar to `/dev/ttyUSB0`:

```bash
python3 serial_collector.py --port /dev/ttyUSB0 --baud 115200 --db data/room_readings.sqlite3
```

Local readings older than `--retention-days` are deleted during periodic prune
runs. Use `--retention-days 0` to disable local retention cleanup.

## Firebase upload

Create a dedicated Firebase Auth user for the Raspberry Pi, then store only
that device account on the Pi.

Required environment variables:

```bash
export FIREBASE_API_KEY=your-firebase-web-api-key
export FIREBASE_DEVICE_EMAIL=room-device@example.com
export FIREBASE_DEVICE_PASSWORD=your-device-password
```

Run manually:

```bash
python3 firebase_uploader.py \
  --port /dev/ttyACM0 \
  --baud 115200 \
  --db data/room_readings.sqlite3 \
  --firebase-database-url https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com \
  --upload-every-seconds 60
```

Hardware-free smoke test:

```bash
printf '%s\n' '{"temperature_c_x100":2642,"humidity_rh_x100":6130,"pressure_pa":100820,"gas_ohm":82345,"gas_valid":1,"heat_stable":1}' \
  | python3 firebase_uploader.py \
      --stdin \
      --db /tmp/room_readings.sqlite3 \
      --firebase-database-url https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com \
      --upload-every-seconds 1
```

For systemd deployment on the Pi:

```bash
sudo bash deploy/install_firebase_collector_service.sh
sudo nano /etc/room-monitor/firebase_collector.env
sudo systemctl restart room-monitor-firebase-collector.service
journalctl -u room-monitor-firebase-collector.service -f
```

## Development test without hardware

```bash
printf '%s\n' '{"temperature_c_x100":2642,"humidity_rh_x100":6130,"pressure_pa":100820,"gas_ohm":82345,"gas_valid":1,"heat_stable":1}' \
  | python3 serial_collector.py --stdin --db /tmp/room_readings.sqlite3
```

Check latest rows:

```bash
sqlite3 /tmp/room_readings.sqlite3 \
  'SELECT measured_at, temperature_c_x100, humidity_rh_x100, pressure_pa, gas_ohm FROM readings ORDER BY id DESC LIMIT 5;'
```
