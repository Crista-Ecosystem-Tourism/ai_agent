from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Index, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import BYTEA

from app.db.models.base import Base, TimestampMixin


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_session"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=None)
    user: Mapped["User"] = relationship(back_populates="sessions")  # type: ignore
    history: Mapped["ChatHistory"] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")  # type: ignore

    session_secret_hash: Mapped[Optional[bytes]] = mapped_column(BYTEA, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    place_ratings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=None)
    places_snapshot: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=None)
    graph_geojson: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=None)

    __table_args__ = (
        Index("idx_chat_session_user_updated", "user_id", "updated_at"),
        Index("idx_chat_session_expires", "expires_at"),
    )

class ChatHistory(Base, TimestampMixin):
    __tablename__ = "chat_history"

    session_id: Mapped[str] = mapped_column(ForeignKey("chat_session.id"), primary_key=True)
    history: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="history")

    __table_args__ = (
        Index("idx_chat_history_expires", "expires_at"),
    )
