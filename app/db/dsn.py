"""Async DSN для SQLAlchemy (asyncpg).

В Docker Compose задаются POSTGRES_*; DATABASE_URL необязателен.
Если задать DATABASE_URL в Coolify/локально — он имеет приоритет.
"""

from __future__ import annotations

import os
from urllib.parse import quote_plus


def get_database_url() -> str:
    raw = os.getenv("DATABASE_URL")
    if raw and raw.strip():
        return raw.strip()

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "crs_agent")

    u = quote_plus(user)
    p = quote_plus(password)
    auth = f"{u}:{p}@{host}" if password != "" else f"{u}@{host}"
    return f"postgresql+asyncpg://{auth}:{port}/{database}"
