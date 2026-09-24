"""Friend invitations and symmetric friendship persistence."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.social_tokens import canonical_friend_pair, hash_invite_code
from app.db.models.auth import User
from app.db.models.social import FriendInvite, Friendship


class SocialInviteNotFoundError(RuntimeError):
    """Invalid, expired, revoked, or already-used invite (kept intentionally uniform)."""


class SocialInviteLimitError(RuntimeError):
    """The account has reached its active invitation limit."""


class SocialService:
    INVITE_TTL = timedelta(days=7)
    MAX_ACTIVE_INVITES = 10

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
