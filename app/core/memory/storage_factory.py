from __future__ import annotations
from typing import Optional
import redis.asyncio as aioredis
import asyncpg

from app.core.memory.protocol import HistoryStore, BackendType
from app.core.memory.config import HistoryConfig
from app.core.memory.redis_store import RedisHistoryStore
from app.core.memory.postgres_store import PostgresHistoryStore
from app.core.memory.sqlalchemy_store.builder import build_history_store

class StorageFactory:
    @staticmethod
    async def create(backend: BackendType, cfg: Optional[HistoryConfig] = None, **kwargs) -> HistoryStore:
        cfg = cfg or HistoryConfig()

        if backend == "redis":
            redis_client: Optional[aioredis.Redis] = kwargs.get("redis_client")
            if not redis_client:
                url = kwargs.get("url")
                redis_client = aioredis.from_url(url, decode_responses=False) if url else aioredis.Redis(
                    host=kwargs.get("host", "localhost"),
                    port=int(kwargs.get("port", 6379)),
                    db=int(kwargs.get("db", 0)),
                    password=kwargs.get("password"),
                    decode_responses=False,
                )
            return RedisHistoryStore(redis_client, cfg)

        if backend == "postgres":
            dsn = kwargs.get("dsn")
            if dsn:
                pool = await asyncpg.create_pool(dsn=dsn, min_size=kwargs.get("min_size", 1), max_size=kwargs.get("max_size", 5))
            else:
                pool = await asyncpg.create_pool(
                    user=kwargs.get("user", "postgres"),
                    password=kwargs.get("password"),
                    database=kwargs.get("database", "postgres"),
                    host=kwargs.get("host", "localhost"),
                    port=kwargs.get("port", 5432),
                    min_size=kwargs.get("min_size", 1),
                    max_size=kwargs.get("max_size", 5),
                )
            store = PostgresHistoryStore(pool, cfg, table=kwargs.get("table", "chat_history"))
            await store.init_schema()
            return store
        
        if backend == "sqlalchemy":
            dsn = kwargs["dsn"]
            return await build_history_store(dsn, cfg)

        raise ValueError(f"Unknown backend: {backend}")
