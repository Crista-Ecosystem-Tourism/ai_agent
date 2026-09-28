#!/usr/bin/env bash
set -euo pipefail

: "${BACKUP_DIR:?Set BACKUP_DIR to the durable backup directory.}"

backup_name="${1:?Pass the PostgreSQL dump filename from BACKUP_DIR.}"
if [[ "$backup_name" == */* || "$backup_name" != crista-postgres-*.dump ]]; then
  echo "Pass only a crista-postgres-*.dump filename from BACKUP_DIR" >&2
  exit 2
fi

database_dump="$BACKUP_DIR/$backup_name"
database_checksum="$database_dump.sha256"
if [[ ! -f "$database_dump" || ! -f "$database_checksum" ]]; then
  echo "PostgreSQL dump or checksum is missing" >&2
  exit 2
fi

(cd "$BACKUP_DIR" && shasum -a 256 -c "$(basename "$database_checksum")")
pg_restore --list "$database_dump" >/dev/null

timestamp="${backup_name#crista-postgres-}"
timestamp="${timestamp%.dump}"
media_archive="$BACKUP_DIR/crista-media-$timestamp.tar.gz"
if [[ -f "$media_archive" ]]; then
  media_checksum="$media_archive.sha256"
  if [[ ! -f "$media_checksum" ]]; then
    echo "Media archive checksum is missing" >&2
    exit 2
  fi
  (cd "$BACKUP_DIR" && shasum -a 256 -c "$(basename "$media_checksum")")
  tar -tzf "$media_archive" >/dev/null
fi

echo "Backup verified: $backup_name"
