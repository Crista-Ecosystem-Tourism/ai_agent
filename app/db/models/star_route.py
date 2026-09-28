from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class StarRouteTranscript(Base, TimestampMixin):
    """An editorially registered transcript with its declared use permission."""

    __tablename__ = "star_route_transcript"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    author_name: Mapped[str | None] = mapped_column(String, nullable=True)
    rights_basis: Mapped[str] = mapped_column(String, nullable=False)
    registered_by: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)


class StarRouteSegment(Base, TimestampMixin):
    """A short, traceable transcript fragment from which a place was extracted."""

    __tablename__ = "star_route_segment"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    transcript_id: Mapped[str] = mapped_column(
        ForeignKey("star_route_transcript.id", ondelete="CASCADE"), nullable=False
    )
    start_seconds: Mapped[int] = mapped_column(nullable=False)
    end_seconds: Mapped[int] = mapped_column(nullable=False)
    excerpt: Mapped[str] = mapped_column(String, nullable=False)
    extracted_place_name: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        Index("idx_star_route_segment_transcript", "transcript_id", "start_seconds"),
    )


class StarRouteCandidate(Base, TimestampMixin):
    """A calculated route that stays private until an editor publishes it."""

    __tablename__ = "star_route_candidate"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    transcript_id: Mapped[str] = mapped_column(
        ForeignKey("star_route_transcript.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    pois: Mapped[list] = mapped_column(JSONB, nullable=False)
    route_geojson: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="review")
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_star_route_candidate_status_published", "status", "published_at"),
        Index("idx_star_route_candidate_transcript", "transcript_id"),
    )
