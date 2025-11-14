# app/memory/sa_store.py
from __future__ import annotations

import json
import asyncpg

from typing import List, Optional
from datetime import datetime, timezone
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

from app.core.memory.config import HistoryConfig
from app.core.memory.utils import _trim_messages


class PostgresHistoryStore:

    def __init__(self, pool: asyncpg.Pool, cfg: HistoryConfig, table: str = "chat_history"):
        self.pool = pool
        self.cfg = cfg
        self.table = table

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table} (
                session_id TEXT PRIMARY KEY,
                history JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at TIMESTAMPTZ NULL
            );
            CREATE INDEX IF NOT EXISTS idx_{self.table}_expires ON {self.table}(expires_at);
            """)

    def _expires_at(self) -> Optional[datetime]:
        if not self.cfg.ttl:
            return None
        return datetime.now(timezone.utc) + self.cfg.ttl

    async def load(self, session_id: str) -> List[ModelMessage]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT history FROM {self.table} WHERE session_id=$1", session_id
            )
            if not row:
                return []
            py = row["history"]
            return ModelMessagesTypeAdapter.validate_python(py)

    async def save(self, session_id: str, messages: List[ModelMessage]) -> None:
        trimmed = _trim_messages(messages, self.cfg.max_messages)
        py_json = json.loads(ModelMessagesTypeAdapter.dump_json(trimmed).decode("utf-8"))
        expires = self._expires_at()
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table} (session_id, history, updated_at, expires_at)
                VALUES ($1, $2, now(), $3)
                ON CONFLICT (session_id)
                DO UPDATE SET history=$2, updated_at=now(), expires_at=$3
                """,
                session_id, py_json, expires
            )

    async def append_and_save(
        self, session_id: str, new_messages: List[ModelMessage]
    ) -> List[ModelMessage]:
        hist = await self.load(session_id)
        hist.extend(new_messages)
        hist = _trim_messages(hist, self.cfg.max_messages)
        await self.save(session_id, hist)
        return hist

    async def delete(self, session_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {self.table} WHERE session_id=$1", session_id
            )

    async def list_sessions(self, limit: int = 100) -> List[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT session_id FROM {self.table} ORDER BY updated_at DESC LIMIT $1",
                limit
            )
            return [r["session_id"] for r in rows]
