from __future__ import annotations
from typing import List
import redis.asyncio as aioredis

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from app.core.memory.config import HistoryConfig
from app.core.memory.utils import _trim_messages


class RedisHistoryStore:
    def __init__(self, redis: aioredis.Redis, cfg: HistoryConfig):
        self.redis = redis
        self.cfg = cfg

    def _key(self, session_id: str) -> str:
        return f"{self.cfg.namespace}:{session_id}:history"

    async def load(self, session_id: str) -> List[ModelMessage]:
        raw = await self.redis.get(self._key(session_id))
        if not raw:
            return []
        return ModelMessagesTypeAdapter.validate_json(raw)

    async def save(self, session_id: str, messages: List[ModelMessage]) -> None:
        data = ModelMessagesTypeAdapter.dump_json(
            _trim_messages(messages, self.cfg.max_messages)
        )
        key = self._key(session_id)
        await self.redis.set(key, data)
        if self.cfg.ttl:
            await self.redis.expire(key, int(self.cfg.ttl.total_seconds()))

    async def append_and_save(
        self, session_id: str, new_messages: List[ModelMessage]
    ) -> List[ModelMessage]:
        hist = await self.load(session_id)
        hist.extend(new_messages)
        hist = _trim_messages(hist, self.cfg.max_messages)
        await self.save(session_id, hist)
        return hist

    async def delete(self, session_id: str) -> None:
        await self.redis.delete(self._key(session_id))

    async def list_sessions(self, limit: int = 100) -> List[str]:
        pattern = f"{self.cfg.namespace}:*:history"
        keys = []
        async for k in self.redis.scan_iter(match=pattern, count=limit):
            keys.append(k.decode() if isinstance(k, bytes) else k)
            if len(keys) >= limit:
                break
        result = []
        for k in keys:
            # "{namespace}:{session_id}:history"
            parts = k.split(":")
            if len(parts) >= 3:
                result.append(parts[1])
        return result
    