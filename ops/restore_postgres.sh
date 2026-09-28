#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to the target PostgreSQL database.}"
: "${BACKUP_DIR:?Set BACKUP_DIR to the durable backup directory.}"

backup_name="${1:?Pass the dump filename from BACKUP_DIR.}"
if [[ "$backup_name" == */* || "$backup_name" != crista-postgres-*.dump ]]; then
  echo "Pass only a crista-postgres-*.dump filename from BACKUP_DIR" >&2
  exit 2
fi
backup_file="$BACKUP_DIR/$backup_name"
checksum_file="$backup_file.sha256"
if [[ ! -f "$backup_file" || ! -f "$checksum_file" ]]; then
  echo "Backup dump or checksum is missing" >&2
  exit 2
fi

if [[ "${CRISTA_RESTORE_CONFIRM:-}" != "restore:$backup_name" ]]; then
  echo "Restore replaces data in DATABASE_URL. Re-run with CRISTA_RESTORE_CONFIRM=restore:$backup_name" >&2
  exit 3
fi

(cd "$BACKUP_DIR" && shasum -a 256 -c "$(basename "$checksum_file")")
pg_restore \
  --dbname="$DATABASE_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --exit-on-error \
  "$backup_file"

echo "PostgreSQL restore complete: $backup_name"
