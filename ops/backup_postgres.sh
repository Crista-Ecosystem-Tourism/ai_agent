#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to the shared Crista PostgreSQL database.}"
: "${BACKUP_DIR:?Set BACKUP_DIR to a durable, access-restricted directory.}"

RETENTION_DAYS="${RETENTION_DAYS:-14}"
if ! [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
  echo "RETENTION_DAYS must be a non-negative integer" >&2
  exit 2
fi

umask 077
mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
database_dump="$BACKUP_DIR/crista-postgres-$timestamp.dump"

pg_dump \
  --dbname="$DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="$database_dump"

shasum -a 256 "$database_dump" > "$database_dump.sha256"

if [[ "${MEDIA_STORAGE_BACKEND:-disabled}" == "local" && -n "${MEDIA_STORAGE_DIR:-}" ]]; then
  if [[ ! -d "$MEDIA_STORAGE_DIR" ]]; then
    echo "MEDIA_STORAGE_DIR does not exist; PostgreSQL backup is retained, media archive was skipped" >&2
  else
    media_archive="$BACKUP_DIR/crista-media-$timestamp.tar.gz"
    tar -C "$MEDIA_STORAGE_DIR" -czf "$media_archive" .
    shasum -a 256 "$media_archive" > "$media_archive.sha256"
  fi
fi

find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'crista-postgres-*.dump' -o -name 'crista-postgres-*.dump.sha256' -o -name 'crista-media-*.tar.gz' -o -name 'crista-media-*.tar.gz.sha256' \) -mtime "+$RETENTION_DAYS" -delete

echo "Backup complete: $(basename "$database_dump")"
