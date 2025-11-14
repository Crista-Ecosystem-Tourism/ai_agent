from __future__ import annotations
from typing import Protocol, List, Literal
from pydantic_ai.messages import ModelMessage


class HistoryStore(Protocol):
    async def load(self, session_id: str) -> List[ModelMessage]:
        ...

    async def save(self, session_id: str, messages: List[ModelMessage]) -> None:
        ...

    async def append_and_save(
        self, session_id: str, new_messages: List[ModelMessage]
    ) -> List[ModelMessage]:
        ...

    async def delete(self, session_id: str) -> None:
        ...

    async def list_sessions(self, limit: int = 100) -> List[str]:
        ...


BackendType = Literal["redis", "postgres", "sqlalchemy"]
