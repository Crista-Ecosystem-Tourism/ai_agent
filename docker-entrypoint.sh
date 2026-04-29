#!/bin/sh
set -eu

# Ещё раз на runtime: bind mount / старый слой мог подложить AppleDouble-файлы.
find /app/alembic -name '._*' -type f -delete 2>/dev/null || true

# Всегда перед стартом приложения: миграции к head.
# Если в Coolify/Docker задан только command с uvicorn, он подставится как "$@"
# и выполнится после upgrade (ENTRYPOINT не затирается при смене CMD).
echo "[docker-entrypoint] alembic upgrade head..."
alembic upgrade head
echo "[docker-entrypoint] starting: $*"
exec "$@"
