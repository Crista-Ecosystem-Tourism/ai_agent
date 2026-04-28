from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Numeric

from app.db.models.base import Base, TimestampMixin


class SuitcaseTrip(Base, TimestampMixin):
    __tablename__ = "suitcase_trip"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    country: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[str] = mapped_column(String(32), nullable=False)
    end_date: Mapped[str] = mapped_column(String(32), nullable=False)
    image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    route_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impressions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photos: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    expenses: Mapped[list["SuitcaseExpense"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )


class SuitcaseExpense(Base, TimestampMixin):
    __tablename__ = "suitcase_expense"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    trip_id: Mapped[str] = mapped_column(
        ForeignKey("suitcase_trip.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    date: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    trip: Mapped["SuitcaseTrip"] = relationship(back_populates="expenses")


class SuitcaseGoal(Base, TimestampMixin):
    __tablename__ = "suitcase_goal"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    color: Mapped[str] = mapped_column(String(32), nullable=False, default="#007AFF")
