#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${ROOM_MONITOR_DB:?ROOM_MONITOR_DB is required}"
BACKUP_DIR="${ROOM_MONITOR_BACKUP_DIR:-/opt/stm32_raspberrypi_practice/backend/backups}"
RETENTION_DAYS="${ROOM_MONITOR_BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_PATH="${BACKUP_DIR}/room_monitor_${TIMESTAMP}.sqlite3"

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${DB_PATH}" ]]; then
  echo "Database not found: ${DB_PATH}" >&2
  exit 0
fi

sqlite3 "${DB_PATH}" ".backup '${BACKUP_PATH}'"
gzip -f "${BACKUP_PATH}"

find "${BACKUP_DIR}" -type f -name 'room_monitor_*.sqlite3.gz' -mtime +"${RETENTION_DAYS}" -delete
echo "Created backup: ${BACKUP_PATH}.gz"
