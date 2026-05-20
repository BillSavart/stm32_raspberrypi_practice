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

To upload each reading to the backend while still keeping the local SQLite copy:

```bash
python3 serial_collector.py \
  --port /dev/serial0 \
  --baud 115200 \
  --db data/room_readings.sqlite3 \
  --upload-url http://SERVER_IP_OR_DOMAIN:8000/api/readings \
  --upload-every-seconds 60 \
  --api-key 'change-this-secret'
```

`--upload-every-seconds` limits backend traffic. The Pi still writes every
received reading to local SQLite, but only uploads the latest accepted reading
when the interval has elapsed.

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
