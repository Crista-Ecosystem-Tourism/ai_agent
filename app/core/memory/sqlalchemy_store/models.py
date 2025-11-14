from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

class ChatHistory(Base):
    __tablename__ = "chat_history"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    history: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_chat_history_expires", "expires_at"),
    )
