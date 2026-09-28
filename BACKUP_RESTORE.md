# Backup and restore runbook

These scripts back up the shared Crista PostgreSQL database. Run them from a host that has `pg_dump`, `pg_restore`, access to the target database, and a durable `BACKUP_DIR` outside the application container filesystem. They never print `DATABASE_URL`.

## Back up

Set the deployment-managed `DATABASE_URL` and an access-restricted backup directory, then run:

```bash
BACKUP_DIR=/srv/backups/crista RETENTION_DAYS=14 ./ops/backup_postgres.sh
```

The script creates a PostgreSQL custom-format dump and SHA-256 sidecar. With `MEDIA_STORAGE_BACKEND=local` and `MEDIA_STORAGE_DIR` set, it also creates a media archive and checksum. Copy both artifacts to independent durable storage before retention removes local copies.

For S3-compatible media, enable bucket versioning and provider backups for the configured prefix. The application keeps media private and does not contain object-storage credentials in a backup artifact.

## Restore

Restore only into an isolated database first. Verify the checksum, database migration head, authenticated login, one Suitcase workspace and one private media object before using the restored database as a recovery target.

The command below replaces data in the target database and therefore requires the dump filename in the confirmation value:

```bash
BACKUP_DIR=/srv/backups/crista \
CRISTA_RESTORE_CONFIRM=restore:crista-postgres-20260101T000000Z.dump \
./ops/restore_postgres.sh crista-postgres-20260101T000000Z.dump
```

Restore a local-media archive only into an empty, access-restricted replacement directory, verify its SHA-256 sidecar, then point `MEDIA_STORAGE_DIR` at that directory. Do not overwrite a live media directory in place.
