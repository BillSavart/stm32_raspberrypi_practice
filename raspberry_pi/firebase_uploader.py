#!/usr/bin/env python3
"""Collect STM32 readings and upload throttled samples to Firebase Realtime Database."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from serial_collector import (
    Reading,
    connect_db,
    insert_reading,
    iter_serial_lines,
    iter_stdin_lines,
    parse_reading,
    print_reading,
    prune_old_readings,
    reading_to_upload_payload,
)


FIREBASE_AUTH_ENDPOINT = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"


@dataclass
class FirebaseSession:
    id_token: str
    refresh_token: str
    expires_at_monotonic: float


def _request_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def firebase_sign_in(api_key: str, email: str, password: str, timeout: float) -> FirebaseSession:
    url = f"{FIREBASE_AUTH_ENDPOINT}?key={urllib.parse.quote(api_key)}"
    response = _request_json(
        url,
        {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        },
        timeout,
    )
    expires_in = int(response.get("expiresIn", "3600"))
    return FirebaseSession(
        id_token=response["idToken"],
        refresh_token=response["refreshToken"],
        expires_at_monotonic=time.monotonic() + max(60, expires_in - 120),
    )


def firebase_database_url(database_url: str, path: str, id_token: str) -> str:
    base = database_url.rstrip("/")
    clean_path = path.strip("/")
    query = urllib.parse.urlencode({"auth": id_token})
    return f"{base}/{clean_path}.json?{query}"


def firebase_request(method: str, url: str, payload: dict[str, Any], timeout: float) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Firebase returned HTTP {response.status}")


def firebase_payload(reading: Reading) -> dict[str, Any]:
    payload = reading_to_upload_payload(reading)
    payload["temperature_c"] = round(reading.temperature_c_x100 / 100.0, 2)
    payload["humidity_rh"] = round(reading.humidity_rh_x100 / 100.0, 2)
    payload["pressure_hpa"] = round(reading.pressure_pa / 100.0, 2)
    return payload


def upload_to_firebase(args: argparse.Namespace, session: FirebaseSession, reading: Reading) -> bool:
    payload = firebase_payload(reading)
    reading_key = reading.measured_at.replace(":", "-").replace(".", "-")

    try:
        latest_url = firebase_database_url(args.firebase_database_url, "latest", session.id_token)
        reading_url = firebase_database_url(args.firebase_database_url, f"readings/{reading_key}", session.id_token)
        firebase_request("PUT", latest_url, payload, args.upload_timeout)
        firebase_request("PUT", reading_url, payload, args.upload_timeout)
        return True
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as exc:
        print(f"firebase upload failed: {exc}", file=sys.stderr, flush=True)
        return False


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def run(args: argparse.Namespace) -> int:
    api_key = args.firebase_api_key or require_env("FIREBASE_API_KEY")
    email = args.firebase_email or require_env("FIREBASE_DEVICE_EMAIL")
    password = args.firebase_password or require_env("FIREBASE_DEVICE_PASSWORD")

    conn = connect_db(args.db)
    source = iter_stdin_lines(sys.stdin) if args.stdin else iter_serial_lines(args.port, args.baud, args.timeout)
    session = firebase_sign_in(api_key, email, password, args.upload_timeout)
    last_upload_monotonic: float | None = None
    last_prune_monotonic = 0.0

    print(f"Collecting STM32 readings into {args.db}", flush=True)
    if not args.stdin:
        print(f"Serial source: {args.port} @ {args.baud}", flush=True)
    print(f"Firebase database: {args.firebase_database_url}", flush=True)
    print(f"Firebase upload interval: every {args.upload_every_seconds}s", flush=True)

    for line in source:
        reading = parse_reading(line)
        if reading is None:
            if args.verbose:
                print(f"ignored: {line.rstrip()}", file=sys.stderr, flush=True)
            continue

        insert_reading(conn, reading)
        now_monotonic = time.monotonic()
        if now_monotonic - last_prune_monotonic >= args.prune_every_seconds:
            prune_old_readings(conn, args.retention_days)
            last_prune_monotonic = now_monotonic

        if last_upload_monotonic is None or now_monotonic - last_upload_monotonic >= args.upload_every_seconds:
            if time.monotonic() >= session.expires_at_monotonic:
                session = firebase_sign_in(api_key, email, password, args.upload_timeout)
            last_upload_monotonic = now_monotonic
            upload_to_firebase(args, session, reading)
        elif args.verbose:
            print("firebase upload skipped: waiting for next upload interval", file=sys.stderr, flush=True)

        print_reading(reading)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read STM32 BME680 JSON lines and upload samples to Firebase.")
    parser.add_argument("--port", default="/dev/serial0", help="UART device path on Raspberry Pi.")
    parser.add_argument("--baud", type=int, default=115200, help="UART baud rate.")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial read timeout in seconds.")
    parser.add_argument("--db", type=Path, default=Path("room_readings.sqlite3"), help="SQLite database path.")
    parser.add_argument("--retention-days", type=int, default=30, help="Delete local readings older than this many days.")
    parser.add_argument(
        "--prune-every-seconds",
        type=float,
        default=3600.0,
        help="Minimum interval between local retention cleanup runs.",
    )
    parser.add_argument("--firebase-database-url", required=True, help="Realtime Database URL.")
    parser.add_argument("--firebase-api-key", help="Firebase Web API key. Defaults to FIREBASE_API_KEY.")
    parser.add_argument("--firebase-email", help="Firebase Auth device email. Defaults to FIREBASE_DEVICE_EMAIL.")
    parser.add_argument("--firebase-password", help="Firebase Auth device password. Defaults to FIREBASE_DEVICE_PASSWORD.")
    parser.add_argument("--upload-timeout", type=float, default=5.0, help="Firebase upload timeout in seconds.")
    parser.add_argument(
        "--upload-every-seconds",
        type=float,
        default=60.0,
        help="Minimum interval between Firebase uploads. Local SQLite still stores every reading.",
    )
    parser.add_argument("--stdin", action="store_true", help="Read JSON lines from stdin instead of a serial port.")
    parser.add_argument("--verbose", action="store_true", help="Print ignored non-reading lines to stderr.")
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
