from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
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
