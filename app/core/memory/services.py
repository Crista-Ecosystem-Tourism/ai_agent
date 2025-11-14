from __future__ import annotations
from typing import List, Protocol, Optional, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic_ai.messages import ModelMessage
from app.core.memory.config import HistoryConfig as HistoryPolicy
from app.core.memory.utils import _trim_messages as _trim


class HistoryStorePort(Protocol):
    async def load(self, session_id: str) -> List[ModelMessage]: ...
    async def save(self, session_id: str, messages: List[ModelMessage], *, expires_at: Optional[datetime] = None) -> None: ...
    async def delete(self, session_id: str) -> None: ...


class ConversationHistoryService:
    def __init__(self, store: HistoryStorePort, policy: HistoryPolicy = HistoryPolicy()):
        self.store = store
        self.policy = policy

    def _expires_at(self) -> Optional[datetime]:
        if not self.policy.ttl:
            return None
        return datetime.now(timezone.utc) + self.policy.ttl

    async def load_for_context(self, session_id: str) -> List[ModelMessage]:
        hist = await self.store.load(session_id)
        return _trim(hist, self.policy.max_messages)

    async def load_full(self, session_id: str) -> List[ModelMessage]:
        return await self.store.load(session_id)

    async def save_full(self, session_id: str, messages: List[ModelMessage]) -> None:
        await self.store.save(session_id, messages, expires_at=self._expires_at())

    async def append_messages(self, session_id: str, new_messages: List[ModelMessage]) -> List[ModelMessage]:
        hist = await self.store.load(session_id)
        hist.extend(new_messages)
        hist = _trim(hist, self.policy.max_messages)
        await self.store.save(session_id, hist, expires_at=self._expires_at())
        return hist

    async def reset(self, session_id: str) -> None:
        await self.store.delete(session_id)
