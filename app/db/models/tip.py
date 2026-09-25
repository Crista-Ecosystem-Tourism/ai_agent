from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class GameTip(Base):
    __tablename__ = "game_tip"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    quest_id: Mapped[str] = mapped_column(ForeignKey("game_quest.id", ondelete="RESTRICT"), nullable=False)
    author_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'review', 'published', 'rejected', 'hidden')", name="game_tip_status"),
        CheckConstraint("length(body) BETWEEN 10 AND 1200", name="game_tip_body_length"),
        Index("idx_game_tip_quest_status", "quest_id", "status", "created_at"),
        Index("idx_game_tip_author_status_updated", "author_id", "status", "updated_at"),
    )


class GameTipReport(Base):
    __tablename__ = "game_tip_report"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tip_id: Mapped[str] = mapped_column(ForeignKey("game_tip.id", ondelete="CASCADE"), nullable=False)
    reporter_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[str | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint("reason IN ('inaccurate', 'unsafe', 'spam', 'copyright', 'other')", name="game_tip_report_reason"),
        CheckConstraint("status IN ('pending', 'resolved', 'dismissed')", name="game_tip_report_status"),
        UniqueConstraint("tip_id", "reporter_id", name="uq_game_tip_reporter_once"),
        Index("idx_game_tip_report_status", "status", "created_at"),
    )


class GameTipModerationAction(Base):
    __tablename__ = "game_tip_moderation_action"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tip_id: Mapped[str | None] = mapped_column(ForeignKey("game_tip.id", ondelete="SET NULL"), nullable=True)
    report_id: Mapped[str | None] = mapped_column(ForeignKey("game_tip_report.id", ondelete="SET NULL"), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_game_tip_action_created", "created_at"),
        Index("idx_game_tip_action_tip", "tip_id", "created_at"),
        Index("idx_game_tip_action_actor_window", "actor_id", "action", "created_at"),
    )
