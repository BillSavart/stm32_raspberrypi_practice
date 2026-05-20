from __future__ import annotations

import os
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field


DATABASE_URL = Path(os.environ.get("ROOM_MONITOR_DB", "data/room_monitor.sqlite3"))
WRITE_API_KEY = os.environ.get("ROOM_MONITOR_WRITE_API_KEY")
READ_API_KEY = os.environ.get("ROOM_MONITOR_READ_API_KEY")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
MAX_BODY_BYTES = int(os.environ.get("ROOM_MONITOR_MAX_BODY_BYTES", "4096"))
RATE_LIMIT_REQUESTS = int(os.environ.get("ROOM_MONITOR_RATE_LIMIT_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("ROOM_MONITOR_RATE_LIMIT_WINDOW_SECONDS", "60"))
RETENTION_DAYS = int(os.environ.get("ROOM_MONITOR_RETENTION_DAYS", "30"))
_REQUEST_LOG: dict[str, deque[float]] = defaultdict(deque)

app = FastAPI(title="Room Monitor API", version="0.1.0")


@app.middleware("http")
async def request_guard(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                body_bytes = int(content_length)
            except ValueError:
                return Response("Invalid Content-Length", status_code=status.HTTP_400_BAD_REQUEST)

            if body_bytes > MAX_BODY_BYTES:
                return Response("Request body too large", status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        request_times = _REQUEST_LOG[client_host]
        while request_times and now - request_times[0] > RATE_LIMIT_WINDOW_SECONDS:
            request_times.popleft()

        if len(request_times) >= RATE_LIMIT_REQUESTS:
            return Response("Rate limit exceeded", status_code=status.HTTP_429_TOO_MANY_REQUESTS)

        request_times.append(now)

    return await call_next(request)


class ReadingIn(BaseModel):
    measured_at: str | None = None
    temperature_c_x100: int
    humidity_rh_x100: int
    pressure_pa: int
    gas_ohm: int = Field(ge=0)
    gas_valid: int = Field(ge=0, le=1)
    heat_stable: int = Field(ge=0, le=1)


class ReadingOut(ReadingIn):
    id: int
    measured_at: str
    temperature_c: float
    humidity_rh: float
    pressure_hpa: float


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def connect_db() -> sqlite3.Connection:
    DATABASE_URL.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
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
            heat_stable INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_measured_at ON readings(measured_at)")
    return conn


def get_db():
    conn = connect_db()
    try:
        yield conn
    finally:
        conn.close()


def require_configured_key(expected_key: str | None, key_name: str, api_key: str | None) -> None:
    if not expected_key:
        raise HTTPException(status_code=503, detail=f"{key_name} is not configured")

    if api_key is None or not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def require_write_key(api_key: Annotated[str | None, Depends(API_KEY_HEADER)]) -> None:
    require_configured_key(WRITE_API_KEY, "ROOM_MONITOR_WRITE_API_KEY", api_key)


def require_read_key(api_key: Annotated[str | None, Depends(API_KEY_HEADER)]) -> None:
    require_configured_key(READ_API_KEY, "ROOM_MONITOR_READ_API_KEY", api_key)


def prune_old_readings(db: sqlite3.Connection) -> None:
    if RETENTION_DAYS <= 0:
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    cutoff_iso = cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")
    db.execute("DELETE FROM readings WHERE measured_at < ?", (cutoff_iso,))


def row_to_reading(row: sqlite3.Row) -> ReadingOut:
    return ReadingOut(
        id=row["id"],
        measured_at=row["measured_at"],
        temperature_c_x100=row["temperature_c_x100"],
        humidity_rh_x100=row["humidity_rh_x100"],
        pressure_pa=row["pressure_pa"],
        gas_ohm=row["gas_ohm"],
        gas_valid=row["gas_valid"],
        heat_stable=row["heat_stable"],
        temperature_c=row["temperature_c_x100"] / 100.0,
        humidity_rh=row["humidity_rh_x100"] / 100.0,
        pressure_hpa=row["pressure_pa"] / 100.0,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/readings",
    response_model=ReadingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_key)],
)
def create_reading(reading: ReadingIn, db: Annotated[sqlite3.Connection, Depends(get_db)]) -> ReadingOut:
    measured_at = reading.measured_at or utc_now_iso()
    try:
        measured_at = parse_utc(measured_at).isoformat(timespec="seconds").replace("+00:00", "Z")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="measured_at must be an ISO-8601 timestamp") from exc

    prune_old_readings(db)
    cursor = db.execute(
        """
        INSERT INTO readings (
            measured_at,
            temperature_c_x100,
            humidity_rh_x100,
            pressure_pa,
            gas_ohm,
            gas_valid,
            heat_stable
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            measured_at,
            reading.temperature_c_x100,
            reading.humidity_rh_x100,
            reading.pressure_pa,
            reading.gas_ohm,
            reading.gas_valid,
            reading.heat_stable,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM readings WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_reading(row)


@app.get("/api/readings/latest", response_model=ReadingOut, dependencies=[Depends(require_read_key)])
def latest_reading(db: Annotated[sqlite3.Connection, Depends(get_db)]) -> ReadingOut:
    row = db.execute("SELECT * FROM readings ORDER BY measured_at DESC, id DESC LIMIT 1").fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No readings found")
    return row_to_reading(row)


@app.get("/api/readings", response_model=list[ReadingOut], dependencies=[Depends(require_read_key)])
def list_readings(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    hours: Annotated[int, Query(ge=1, le=168)] = 24,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[ReadingOut]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    since_iso = since.isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = db.execute(
        """
        SELECT *
        FROM readings
        WHERE measured_at >= ?
        ORDER BY measured_at DESC, id DESC
        LIMIT ?
        """,
        (since_iso, limit),
    ).fetchall()
    return [row_to_reading(row) for row in rows]
