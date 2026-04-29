# syntax=docker/dockerfile:1.6

# ── Builder ────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# BuildKit apt-cache: keep /var/cache/apt and /var/lib/apt across builds.
# rm /etc/apt/apt.conf.d/docker-clean — иначе apt вычистит кеш в конце шага.
RUN rm -f /etc/apt/apt.conf.d/docker-clean
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ── Runtime ────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

RUN rm -f /etc/apt/apt.conf.d/docker-clean
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
 && apt-get install -y --no-install-recommends libpq5

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY . .

# macOS копирует на диск служебные `._*` (AppleDouble). Они попадают в `alembic/versions/`
# с расширением `.py` — Alembic пытается exec_module и падает с "null bytes".
RUN find /app/alembic -name '._*' -type f -delete 2>/dev/null || true \
 && find /app -maxdepth 2 -name '._*' -type f -delete 2>/dev/null || true

EXPOSE 8002

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
