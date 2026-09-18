from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class GameContentRevision(Base, TimestampMixin):
    """A published, immutable revision of a small learning experience."""

    __tablename__ = "game_content_revision"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GameProfile(Base, TimestampMixin):
    __tablename__ = "game_profile"

    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    energy: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    energy_refreshed_on: Mapped[date] = mapped_column(Date, nullable=False)
    streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class GameCountry(Base, TimestampMixin):
    __tablename__ = "game_country"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class GameRegion(Base, TimestampMixin):
    __tablename__ = "game_region"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    country_id: Mapped[str] = mapped_column(ForeignKey("game_country.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("country_id", "position", name="uq_game_region_country_position"),
    )


class GameCity(Base, TimestampMixin):
    __tablename__ = "game_city"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("game_region.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    required_quest_count: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    completion_stamp_key: Mapped[str | None] = mapped_column(String, nullable=True)
    completion_stamp_title: Mapped[str | None] = mapped_column(String, nullable=True)
    boss_content_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("game_content_revision.id"), nullable=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_game_city_region", "region_id"),
    )


class GameDistrict(Base, TimestampMixin):
    __tablename__ = "game_district"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    city_id: Mapped[str] = mapped_column(ForeignKey("game_city.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("city_id", "position", name="uq_game_district_city_position"),
    )


class GameQuest(Base, TimestampMixin):
    __tablename__ = "game_quest"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    city_id: Mapped[str] = mapped_column(ForeignKey("game_city.id"), nullable=False)
    content_revision_id: Mapped[str] = mapped_column(
        ForeignKey("game_content_revision.id"), nullable=False
    )
    district_id: Mapped[str | None] = mapped_column(ForeignKey("game_district.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    prerequisite_quest_id: Mapped[str | None] = mapped_column(
        ForeignKey("game_quest.id"), nullable=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("city_id", "position", name="uq_game_quest_city_position"),
        Index("idx_game_quest_city_published", "city_id", "is_published"),
    )


class GameQuestCompletion(Base):
    __tablename__ = "game_quest_completion"

    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    quest_id: Mapped[str] = mapped_column(ForeignKey("game_quest.id"), primary_key=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GameAttempt(Base):
    __tablename__ = "game_attempt"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    content_revision_id: Mapped[str] = mapped_column(
        ForeignKey("game_content_revision.id"), nullable=False
    )
    interaction_key: Mapped[str] = mapped_column(String, nullable=False)
    answer_key: Mapped[str] = mapped_column(String, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_game_attempt_user_created", "user_id", "created_at"),
    )


class GameStamp(Base):
    __tablename__ = "game_stamp"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    stamp_key: Mapped[str] = mapped_column(String, nullable=False)
    content_revision_id: Mapped[str] = mapped_column(
        ForeignKey("game_content_revision.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "stamp_key", name="uq_game_stamp_user_key"),
        Index("idx_game_stamp_user_earned", "user_id", "earned_at"),
    )


class GameRewardLedger(Base):
    """Immutable XP receipt. A unique reward key makes retries harmless."""

    __tablename__ = "game_reward_ledger"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    quest_id: Mapped[str] = mapped_column(ForeignKey("game_quest.id"), nullable=False)
    reward_key: Mapped[str] = mapped_column(String, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "reward_key", name="uq_game_reward_user_key"),
        Index("idx_game_reward_user_awarded", "user_id", "awarded_at"),
    )


class GameDailyProgress(Base):
    __tablename__ = "game_daily_progress"

    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    goal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    completed_quests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goal_reached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
