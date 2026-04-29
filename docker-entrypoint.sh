#!/bin/sh
set -eu

# Всегда перед стартом приложения: миграции к head.
# Если в Coolify/Docker задан только command с uvicorn, он подставится как "$@"
# и выполнится после upgrade (ENTRYPOINT не затирается при смене CMD).
echo "[docker-entrypoint] alembic upgrade head..."
alembic upgrade head
echo "[docker-entrypoint] starting: $*"
exec "$@"
