from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

from app.core.memory.config import HistoryConfig
from app.core.memory.utils import _trim_messages
from app.db.models.chat import ChatHistory


class SqlAlchemyHistoryStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], cfg: HistoryConfig):
        self.session_factory = session_factory
        self.cfg = cfg

    def _expires_at(self) -> Optional[datetime]:
        return datetime.now(timezone.utc) + self.cfg.ttl if self.cfg.ttl else None

    async def load(self, session_id: str) -> List[ModelMessage]:
        async with self.session_factory() as s:
            row = (await s.execute(
                select(ChatHistory.history).where(ChatHistory.session_id == session_id)
            )).scalar_one_or_none()
            if not row:
                return []
            return ModelMessagesTypeAdapter.validate_python(row)

    async def save(
        self,
        session_id: str,
        messages: List[ModelMessage],
        *,
        expires_at: Optional[datetime] = None,
    ) -> None:
        import json
        py_json = json.loads(ModelMessagesTypeAdapter.dump_json(messages).decode("utf-8"))

        now = datetime.now(timezone.utc)
        if expires_at is None:
            expires_at = self._expires_at()

        async with self.session_factory() as s:
            exists = (await s.execute(
                select(ChatHistory.session_id).where(ChatHistory.session_id == session_id)
            )).scalar_one_or_none()

            if exists:
                await s.execute(
                    update(ChatHistory)
                    .where(ChatHistory.session_id == session_id)
                    .values(history=py_json, updated_at=now, expires_at=expires_at)
                )
            else:
                await s.execute(
                    insert(ChatHistory).values(
                        session_id=session_id,
                        history=py_json,
                        created_at=now,
                        updated_at=now,
                        expires_at=expires_at,
                    )
                )
            await s.commit()

    async def append_and_save(self, session_id: str, new_messages: List[ModelMessage]) -> List[ModelMessage]:
        hist = await self.load(session_id)
        hist.extend(new_messages)
        hist = _trim_messages(hist, self.cfg.max_messages)
        await self.save(session_id, hist)
        return hist

    async def delete(self, session_id: str) -> None:
        async with self.session_factory() as s:
            await s.execute(delete(ChatHistory).where(ChatHistory.session_id == session_id))
            await s.commit()

    async def list_sessions(self, limit: int = 100) -> List[str]:
        async with self.session_factory() as s:
            rows = (await s.execute(
                select(ChatHistory.session_id)
                .order_by(ChatHistory.updated_at.desc())
                .limit(limit)
            )).scalars().all()
            return list(rows)
