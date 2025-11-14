from __future__ import annotations
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.memory.sqlalchemy_store.store import SqlAlchemyHistoryStore, HistoryConfig


async def build_history_store(pg_dsn: str, cfg: Optional[HistoryConfig] = None) -> SqlAlchemyHistoryStore:
    engine = create_async_engine(pg_dsn, pool_pre_ping=True, future=True)
    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)
    return SqlAlchemyHistoryStore(session_factory, cfg or HistoryConfig())
