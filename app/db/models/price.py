from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class PriceObservation(Base, TimestampMixin):
    """A sourced price quote; stale rows are never presented as current."""
    __tablename__ = "price_observation"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    subject_key: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(48), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="price_observation_nonnegative"),
        CheckConstraint("char_length(currency) = 3", name="price_observation_currency"),
        CheckConstraint("expires_at > observed_at", name="price_observation_positive_ttl"),
        Index("idx_price_observation_subject_freshness", "subject_key", "expires_at", "observed_at"),
    )


class PriceWatch(Base, TimestampMixin):
    __tablename__ = "price_watch"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(200), nullable=False)
    threshold_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_alerted_amount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("threshold_minor >= 0", name="price_watch_nonnegative_threshold"),
        CheckConstraint("char_length(currency) = 3", name="price_watch_currency"),
        UniqueConstraint("user_id", "subject_key", "currency", name="uq_price_watch_user_subject_currency"),
        Index("idx_price_watch_active_subject", "active", "subject_key"),
    )
