from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from app.db.models.base import Base, TimestampMixin


class SavedRoute(Base, TimestampMixin):
    __tablename__ = "saved_route"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("chat_session.id"), nullable=True)
    places: Mapped[dict] = mapped_column(JSONB, nullable=False)
    graph_geojson: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=None)

    user: Mapped["User"] = relationship()  # type: ignore

    __table_args__ = (
        Index("idx_saved_route_user", "user_id"),
    )
