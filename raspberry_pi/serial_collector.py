#!/usr/bin/env python3
"""Collect JSON-line readings from the STM32 and store them in SQLite."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TextIO


REQUIRED_FIELDS = (
    "temperature_c_x100",
    "humidity_rh_x100",
    "pressure_pa",
    "gas_ohm",
    "gas_valid",
    "heat_stable",
)


@dataclass(frozen=True)
class Reading:
    measured_at: str
    temperature_c_x100: int
    humidity_rh_x100: int
    pressure_pa: int
    gas_ohm: int
    gas_valid: int
    heat_stable: int
    raw_json: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_at TEXT NOT NULL,
            temperature_c_x100 INTEGER NOT NULL,
            humidity_rh_x100 INTEGER NOT NULL,
            pressure_pa INTEGER NOT NULL,
            gas_ohm INTEGER NOT NULL,
            gas_valid INTEGER NOT NULL,
            heat_stable INTEGER NOT NULL,
            raw_json TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_measured_at ON readings(measured_at)")
    return conn


def parse_reading(line: str) -> Reading | None:
    stripped = line.strip()
    if not stripped or not stripped.startswith("{"):
        return None

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if not all(field in payload for field in REQUIRED_FIELDS):
        return None

    try:
        values = {field: int(payload[field]) for field in REQUIRED_FIELDS}
    except (TypeError, ValueError):
        return None

    return Reading(measured_at=utc_now_iso(), raw_json=stripped, **values)


def insert_reading(conn: sqlite3.Connection, reading: Reading) -> None:
    conn.execute(
        """
        INSERT INTO readings (
            measured_at,
            temperature_c_x100,
            humidity_rh_x100,
            pressure_pa,
            gas_ohm,
            gas_valid,
            heat_stable,
            raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reading.measured_at,
            reading.temperature_c_x100,
            reading.humidity_rh_x100,
            reading.pressure_pa,
            reading.gas_ohm,
            reading.gas_valid,
            reading.heat_stable,
            reading.raw_json,
        ),
    )
    conn.commit()


def reading_to_upload_payload(reading: Reading) -> dict[str, int | str]:
    return {
        "measured_at": reading.measured_at,
        "temperature_c_x100": reading.temperature_c_x100,
        "humidity_rh_x100": reading.humidity_rh_x100,
        "pressure_pa": reading.pressure_pa,
        "gas_ohm": reading.gas_ohm,
        "gas_valid": reading.gas_valid,
        "heat_stable": reading.heat_stable,
    }


def upload_reading(upload_url: str, reading: Reading, timeout: float, api_key: str | None) -> bool:
    body = json.dumps(reading_to_upload_payload(reading)).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    request = urllib.request.Request(
        upload_url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"upload failed: {exc}", file=sys.stderr, flush=True)
        return False


def iter_stdin_lines(stdin: TextIO) -> Iterable[str]:
    for line in stdin:
        yield line


def iter_serial_lines(port: str, baud: int, timeout: float) -> Iterable[str]:
    try:
        import serial
    except ImportError as exc:
        raise SystemExit("pyserial is not installed. Run: python3 -m pip install -r requirements.txt") from exc

    with serial.Serial(port=port, baudrate=baud, timeout=timeout) as ser:
        ser.reset_input_buffer()
        while True:
            raw = ser.readline()
            if not raw:
                continue
            yield raw.decode("utf-8", errors="replace")


def print_reading(reading: Reading) -> None:
    temp_c = reading.temperature_c_x100 / 100.0
    humidity = reading.humidity_rh_x100 / 100.0
    pressure_hpa = reading.pressure_pa / 100.0
    print(
        f"{reading.measured_at} "
        f"temp={temp_c:.2f}C "
        f"humidity={humidity:.2f}% "
        f"pressure={pressure_hpa:.2f}hPa "
        f"gas={reading.gas_ohm}ohm "
        f"gas_valid={reading.gas_valid} "
        f"heat_stable={reading.heat_stable}",
        flush=True,
    )


def run(args: argparse.Namespace) -> int:
    conn = connect_db(args.db)
    source = iter_stdin_lines(sys.stdin) if args.stdin else iter_serial_lines(args.port, args.baud, args.timeout)

    print(f"Collecting STM32 readings into {args.db}", flush=True)
    if not args.stdin:
        print(f"Serial source: {args.port} @ {args.baud}", flush=True)
    if args.upload_url:
        print(f"Upload target: {args.upload_url}", flush=True)

    for line in source:
        reading = parse_reading(line)
        if reading is None:
            if args.verbose:
                print(f"ignored: {line.rstrip()}", file=sys.stderr, flush=True)
            continue

        insert_reading(conn, reading)
        if args.upload_url:
            upload_reading(args.upload_url, reading, args.upload_timeout, args.api_key)
        print_reading(reading)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read STM32 BME680 JSON lines and store them in SQLite.")
    parser.add_argument("--port", default="/dev/serial0", help="UART device path on Raspberry Pi.")
    parser.add_argument("--baud", type=int, default=115200, help="UART baud rate.")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial read timeout in seconds.")
    parser.add_argument("--db", type=Path, default=Path("room_readings.sqlite3"), help="SQLite database path.")
    parser.add_argument("--upload-url", help="Optional backend POST /api/readings URL.")
    parser.add_argument("--upload-timeout", type=float, default=3.0, help="Backend upload timeout in seconds.")
    parser.add_argument("--api-key", help="Optional backend API key sent as X-API-Key.")
    parser.add_argument("--stdin", action="store_true", help="Read JSON lines from stdin instead of a serial port.")
    parser.add_argument("--verbose", action="store_true", help="Print ignored non-reading lines to stderr.")
    return parser


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
