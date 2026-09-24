"""Friend invitations and symmetric friendship persistence."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.social_tokens import (
    can_add_team_member,
    can_change_team_role,
    can_remove_team_member,
    canonical_friend_pair,
    hash_invite_code,
)
from app.db.models.auth import User
from app.db.models.social import FriendInvite, Friendship, SocialTeam, SocialTeamMembership


class SocialInviteNotFoundError(RuntimeError):
    """Invalid, expired, revoked, or already-used invite (kept intentionally uniform)."""


class SocialInviteLimitError(RuntimeError):
    """The account has reached its active invitation limit."""


class SocialTeamNotFoundError(RuntimeError):
    """The team, membership, or eligible friend does not exist for this caller."""


class SocialTeamPermissionError(RuntimeError):
    """The caller's team role does not authorize this operation."""


class SocialTeamLimitError(RuntimeError):
    """The account or team reached a configured size limit."""


class SocialService:
    INVITE_TTL = timedelta(days=7)
    MAX_ACTIVE_INVITES = 10
    MAX_TEAMS_PER_USER = 10
    MAX_TEAM_SIZE = 20

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32),
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.session_factory = session_factory
        self._token_factory = token_factory
        self._clock = clock

    async def create_friend_invite(self, inviter_id: str) -> dict:
        code = self._token_factory()
        now = self._clock()
        async with self.session_factory() as db:
            inviter = await db.scalar(
                select(User.id).where(User.id == inviter_id).with_for_update()
            )
            if inviter is None:
                raise SocialInviteNotFoundError
            active_count = await db.scalar(
                select(func.count()).select_from(FriendInvite).where(
                    FriendInvite.inviter_id == inviter_id,
                    FriendInvite.accepted_at.is_(None),
                    FriendInvite.revoked_at.is_(None),
                    FriendInvite.expires_at > now,
                )
            )
            if (active_count or 0) >= self.MAX_ACTIVE_INVITES:
                raise SocialInviteLimitError
            invite = FriendInvite(
                id=uuid.uuid4().hex,
                token_hash=hash_invite_code(code),
                inviter_id=inviter_id,
                created_at=now,
                expires_at=now + self.INVITE_TTL,
            )
            db.add(invite)
            await db.commit()
        return {
            "invite_id": invite.id,
            "invite_code": code,
            "expires_at": invite.expires_at.isoformat(),
        }

    async def accept_friend_invite(self, recipient_id: str, code: str) -> dict:
        now = self._clock()
        async with self.session_factory() as db:
            invite = await db.scalar(
                select(FriendInvite)
                .where(FriendInvite.token_hash == hash_invite_code(code))
                .with_for_update()
            )
            if invite is None or invite.revoked_at is not None:
                raise SocialInviteNotFoundError
            if invite.accepted_at is not None:
                if invite.accepted_by_id == recipient_id:
                    return {"friend_id": invite.inviter_id, "created": False}
                raise SocialInviteNotFoundError
            if invite.expires_at <= now or invite.inviter_id == recipient_id:
                raise SocialInviteNotFoundError

            user_a_id, user_b_id = canonical_friend_pair(invite.inviter_id, recipient_id)
            result = await db.execute(
                pg_insert(Friendship)
                .values(user_a_id=user_a_id, user_b_id=user_b_id, created_at=now)
                .on_conflict_do_nothing(index_elements=["user_a_id", "user_b_id"])
            )
            invite.accepted_by_id = recipient_id
            invite.accepted_at = now
            await db.commit()
            return {"friend_id": invite.inviter_id, "created": result.rowcount == 1}

    async def list_friends(self, user_id: str) -> list[dict]:
        async with self.session_factory() as db:
            first_direction = await db.execute(
                select(User.id, User.name, Friendship.created_at)
                .join(Friendship, Friendship.user_b_id == User.id)
                .where(Friendship.user_a_id == user_id)
            )
            second_direction = await db.execute(
                select(User.id, User.name, Friendship.created_at)
                .join(Friendship, Friendship.user_a_id == User.id)
                .where(Friendship.user_b_id == user_id)
            )
            rows = [*first_direction.all(), *second_direction.all()]
            rows.sort(key=lambda row: (row.name or "").casefold())
            return [
                {"id": row.id, "name": row.name, "friends_since": row.created_at.isoformat()}
                for row in rows
            ]

    async def remove_friend(self, user_id: str, friend_id: str) -> None:
        if user_id == friend_id:
            raise SocialInviteNotFoundError
        user_a_id, user_b_id = canonical_friend_pair(user_id, friend_id)
        async with self.session_factory() as db:
            await db.execute(
                update(FriendInvite)
                .where(
                    or_(
                        and_(FriendInvite.inviter_id == user_id, FriendInvite.accepted_by_id == friend_id),
                        and_(FriendInvite.inviter_id == friend_id, FriendInvite.accepted_by_id == user_id),
                    ),
                    FriendInvite.accepted_at.is_not(None),
                    FriendInvite.revoked_at.is_(None),
                )
                .values(revoked_at=self._clock())
            )
            await db.execute(
                delete(Friendship).where(
                    Friendship.user_a_id == user_a_id,
                    Friendship.user_b_id == user_b_id,
                )
            )
            await db.commit()

    async def revoke_friend_invite(self, inviter_id: str, invite_id: str) -> None:
        now = self._clock()
        async with self.session_factory() as db:
            invite = await db.scalar(
                select(FriendInvite)
                .where(FriendInvite.id == invite_id, FriendInvite.inviter_id == inviter_id)
                .with_for_update()
            )
            if (
                invite is None
                or invite.accepted_at is not None
                or invite.revoked_at is not None
                or invite.expires_at <= now
            ):
                raise SocialInviteNotFoundError
            invite.revoked_at = now
            await db.commit()

    async def list_teams(self, user_id: str) -> list[dict]:
        async with self.session_factory() as db:
            teams = (await db.execute(
                select(SocialTeam, SocialTeamMembership.role)
                .join(SocialTeamMembership, SocialTeamMembership.team_id == SocialTeam.id)
                .where(SocialTeamMembership.user_id == user_id)
                .order_by(SocialTeam.created_at.desc())
            )).all()
            if not teams:
                return []
            team_ids = [team.id for team, _role in teams]
            member_rows = (await db.execute(
                select(
                    SocialTeamMembership.team_id,
                    User.id,
                    User.name,
                    SocialTeamMembership.role,
                    SocialTeamMembership.joined_at,
                )
                .join(User, User.id == SocialTeamMembership.user_id)
                .where(SocialTeamMembership.team_id.in_(team_ids))
                .order_by(SocialTeamMembership.joined_at, User.name)
            )).all()
            members_by_team: dict[str, list[dict]] = {team_id: [] for team_id in team_ids}
            for row in member_rows:
                members_by_team[row.team_id].append({
                    "id": row.id,
                    "name": row.name,
                    "role": row.role,
                    "joined_at": row.joined_at.isoformat(),
                })
            return [
                {
                    "id": team.id,
                    "name": team.name,
                    "role": role,
                    "created_at": team.created_at.isoformat(),
                    "members": members_by_team[team.id],
                }
                for team, role in teams
            ]

    async def create_team(self, user_id: str, name: str) -> dict:
        normalized_name = " ".join(name.split())
        if not normalized_name or len(normalized_name) > 80:
            raise ValueError("Team name must contain 1 to 80 characters")
        now = self._clock()
        async with self.session_factory() as db:
            user_exists = await db.scalar(select(User.id).where(User.id == user_id).with_for_update())
            if user_exists is None:
                raise SocialTeamNotFoundError
            count = await db.scalar(
                select(func.count()).select_from(SocialTeamMembership).where(
                    SocialTeamMembership.user_id == user_id,
                    SocialTeamMembership.role == "owner",
                )
            )
            if (count or 0) >= self.MAX_TEAMS_PER_USER:
                raise SocialTeamLimitError
            team = SocialTeam(
                id=uuid.uuid4().hex,
                name=normalized_name,
                created_by_id=user_id,
                created_at=now,
            )
            db.add(team)
            db.add(SocialTeamMembership(
                team_id=team.id,
                user_id=user_id,
                role="owner",
                joined_at=now,
            ))
            await db.commit()
            return {"id": team.id, "name": team.name, "role": "owner", "created_at": now.isoformat(), "members": [
                {"id": user_id, "name": None, "role": "owner", "joined_at": now.isoformat()},
            ]}

    async def add_team_member(self, actor_id: str, team_id: str, friend_id: str) -> bool:
        async with self.session_factory() as db:
            team = await db.scalar(select(SocialTeam).where(SocialTeam.id == team_id).with_for_update())
            if team is None:
                raise SocialTeamNotFoundError
            actor_role = await self._team_role(db, team_id, actor_id)
            if not can_add_team_member(actor_role or "", "member"):
                raise SocialTeamPermissionError
            try:
                friend_a, friend_b = canonical_friend_pair(actor_id, friend_id)
            except ValueError as exc:
                raise SocialTeamNotFoundError from exc
            friendship = await db.scalar(select(Friendship.user_a_id).where(
                Friendship.user_a_id == friend_a, Friendship.user_b_id == friend_b,
            ))
            if friendship is None:
                raise SocialTeamNotFoundError
            existing = await db.get(SocialTeamMembership, (team_id, friend_id))
            if existing is not None:
                await db.commit()
                return False
            size = await db.scalar(select(func.count()).select_from(SocialTeamMembership).where(
                SocialTeamMembership.team_id == team_id,
            ))
            if (size or 0) >= self.MAX_TEAM_SIZE:
                raise SocialTeamLimitError
            db.add(SocialTeamMembership(
                team_id=team_id,
                user_id=friend_id,
                role="member",
                joined_at=self._clock(),
            ))
            await db.commit()
            return True

    async def change_team_role(self, actor_id: str, team_id: str, member_id: str, role: str) -> bool:
        async with self.session_factory() as db:
            await self._lock_team(db, team_id)
            actor_role = await self._team_role(db, team_id, actor_id)
            target = await db.get(SocialTeamMembership, (team_id, member_id))
            if target is None:
                raise SocialTeamNotFoundError
            if not can_change_team_role(actor_role or "", target.role, role):
                raise SocialTeamPermissionError
            if target.role == role:
                await db.commit()
                return False
            target.role = role
            await db.commit()
            return True

    async def remove_team_member(self, actor_id: str, team_id: str, member_id: str) -> bool:
        async with self.session_factory() as db:
            await self._lock_team(db, team_id)
            actor_role = await self._team_role(db, team_id, actor_id)
            target = await db.get(SocialTeamMembership, (team_id, member_id))
            if target is None:
                raise SocialTeamNotFoundError
            if not can_remove_team_member(actor_role or "", target.role, actor_id == member_id):
                raise SocialTeamPermissionError
            await db.delete(target)
            await db.commit()
            return True

    @staticmethod
    async def _lock_team(db: AsyncSession, team_id: str) -> SocialTeam:
        team = await db.scalar(select(SocialTeam).where(SocialTeam.id == team_id).with_for_update())
        if team is None:
            raise SocialTeamNotFoundError
        return team

    @staticmethod
    async def _team_role(db: AsyncSession, team_id: str, user_id: str) -> str | None:
        return await db.scalar(select(SocialTeamMembership.role).where(
            SocialTeamMembership.team_id == team_id,
            SocialTeamMembership.user_id == user_id,
        ))
