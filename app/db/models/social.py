from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class FriendInvite(Base):
    __tablename__ = "friend_invite"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    inviter_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    accepted_by_id: Mapped[str | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("accepted_by_id IS NULL OR accepted_by_id <> inviter_id", name="friend_invite_not_self_accepted"),
        Index("idx_friend_invite_inviter_created", "inviter_id", "created_at"),
        Index("idx_friend_invite_expires", "expires_at"),
    )


class Friendship(Base):
    __tablename__ = "friendship"

    user_a_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    user_b_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("user_a_id < user_b_id", name="friendship_canonical_user_order"),
        Index("idx_friendship_user_b", "user_b_id"),
    )


class SocialTeam(Base):
    __tablename__ = "social_team"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("idx_social_team_creator", "created_by_id", "created_at"),)


class SocialTeamMembership(Base):
    __tablename__ = "social_team_membership"

    team_id: Mapped[str] = mapped_column(ForeignKey("social_team.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('owner', 'admin', 'member')", name="social_team_membership_role"),
        Index("idx_social_team_membership_user", "user_id", "team_id"),
    )


class SocialTeamQuest(Base):
    __tablename__ = "social_team_quest"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("social_team.id", ondelete="CASCADE"), nullable=False)
    quest_id: Mapped[str] = mapped_column(ForeignKey("game_quest.id", ondelete="RESTRICT"), nullable=False)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    reward_xp: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("reward_xp >= 1", name="social_team_quest_positive_xp"),
        CheckConstraint("status IN ('active', 'complete')", name="social_team_quest_status"),
        UniqueConstraint("team_id", "quest_id", name="uq_social_team_quest_once"),
        Index("idx_social_team_quest_status", "team_id", "status"),
    )


class SocialTeamQuestParticipant(Base):
    __tablename__ = "social_team_quest_participant"

    team_quest_id: Mapped[str] = mapped_column(
        ForeignKey("social_team_quest.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("idx_social_team_quest_participant_user", "user_id", "team_quest_id"),)
