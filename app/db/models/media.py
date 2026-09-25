from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class GameMediaAsset(Base):
    __tablename__ = "game_media_asset"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    quest_id: Mapped[str] = mapped_column(ForeignKey("game_quest.id", ondelete="CASCADE"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    preview_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("content_type IN ('image/jpeg', 'video/mp4', 'video/webm')", name="game_media_type_allowed"),
        CheckConstraint("byte_size BETWEEN 1 AND 52428800", name="game_media_size_limit"),
        CheckConstraint("width > 0 AND height > 0", name="game_media_dimensions_positive"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds BETWEEN 1 AND 60", name="game_media_duration_limit"),
        Index("idx_game_media_owner_created", "owner_id", "created_at"),
        Index("idx_game_media_quest_created", "quest_id", "created_at"),
    )
