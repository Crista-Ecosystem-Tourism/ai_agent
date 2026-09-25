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
from app.core.league_policy import LeagueScore, LeagueWeek, league_week, settle_weekly_ranks
from app.db.models.auth import User
from app.db.models.game import (
    GameCity,
    GameContentRevision,
    GameContentTranslation,
    GameQuest,
    GameQuestCompletion,
    GameRewardLedger,
)
from app.db.models.social import (
    FriendInvite,
    Friendship,
    LeagueMembership,
    LeagueSeason,
    SocialTeam,
    SocialTeamMembership,
    SocialTeamQuest,
    SocialTeamQuestParticipant,
)
from app.services.game_progress import GameProgressService


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


class SocialSharedQuestUnavailableError(RuntimeError):
    """The source game quest is not published or cannot provide a safe reward."""


class SocialSharedQuestExistsError(RuntimeError):
    """A team can run a particular published quest only once."""


class SocialSharedQuestTeamTooSmallError(RuntimeError):
    """A shared quest needs at least two active team participants."""


class SocialService:
    INVITE_TTL = timedelta(days=7)
    MAX_ACTIVE_INVITES = 10
    MAX_TEAMS_PER_USER = 10
    MAX_TEAM_SIZE = 20

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        game_progress: GameProgressService,
        token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32),
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.session_factory = session_factory
        self.game_progress = game_progress
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
            active_team_quests = select(SocialTeamQuest.id).where(
                SocialTeamQuest.team_id == team_id,
                SocialTeamQuest.status == "active",
            )
            await db.execute(delete(SocialTeamQuestParticipant).where(
                SocialTeamQuestParticipant.team_quest_id.in_(active_team_quests),
                SocialTeamQuestParticipant.user_id == member_id,
            ))
            await db.delete(target)
            await db.commit()
            return True

    async def create_shared_quest(self, actor_id: str, team_id: str, quest_id: str) -> dict:
        now = self._clock()
        async with self.session_factory() as db:
            await self._lock_team(db, team_id)
            actor_role = await self._team_role(db, team_id, actor_id)
            if actor_role not in {"owner", "admin"}:
                raise SocialTeamPermissionError
            quest_and_content = await db.execute(
                select(GameQuest, GameContentRevision)
                .join(GameContentRevision, GameContentRevision.id == GameQuest.content_revision_id)
                .where(
                    GameQuest.id == quest_id,
                    GameQuest.is_published.is_(True),
                    GameContentRevision.is_published.is_(True),
                )
            )
            source = quest_and_content.one_or_none()
            if source is None:
                raise SocialSharedQuestUnavailableError
            quest, content = source
            reward = content.payload.get("reward", {})
            reward_xp = reward.get("xp") if isinstance(reward, dict) else None
            if isinstance(reward_xp, bool) or not isinstance(reward_xp, int) or reward_xp < 1 or reward_xp > 1000:
                raise SocialSharedQuestUnavailableError
            existing = await db.scalar(select(SocialTeamQuest.id).where(
                SocialTeamQuest.team_id == team_id,
                SocialTeamQuest.quest_id == quest.id,
            ))
            if existing is not None:
                raise SocialSharedQuestExistsError
            participants = list((await db.scalars(
                select(SocialTeamMembership.user_id).where(SocialTeamMembership.team_id == team_id)
            )).all())
            if len(participants) < 2:
                raise SocialSharedQuestTeamTooSmallError
            shared_quest = SocialTeamQuest(
                id=uuid.uuid4().hex,
                team_id=team_id,
                quest_id=quest.id,
                created_by_id=actor_id,
                reward_xp=reward_xp,
                status="active",
                created_at=now,
            )
            db.add(shared_quest)
            for participant_id in participants:
                db.add(SocialTeamQuestParticipant(
                    team_quest_id=shared_quest.id,
                    user_id=participant_id,
                    joined_at=now,
                ))
            await db.commit()
            return await self._shared_quest_payload(db, shared_quest)

    async def list_shared_quest_catalog(self, language: str = "ru") -> list[dict]:
        language = "en" if language == "en" else "ru"
        async with self.session_factory() as db:
            rows = (await db.execute(
                select(
                    GameQuest.id.label("quest_id"),
                    GameCity.id.label("city_id"),
                    GameCity.name.label("city_name"),
                    GameContentRevision.payload,
                    GameContentTranslation.payload.label("translated_payload"),
                )
                .join(GameCity, GameCity.id == GameQuest.city_id)
                .join(GameContentRevision, GameContentRevision.id == GameQuest.content_revision_id)
                .outerjoin(
                    GameContentTranslation,
                    and_(
                        GameContentTranslation.content_revision_id == GameContentRevision.id,
                        GameContentTranslation.language == language,
                        GameContentTranslation.is_published.is_(True),
                    ),
                )
                .where(
                    GameCity.is_published.is_(True),
                    GameQuest.is_published.is_(True),
                    GameContentRevision.is_published.is_(True),
                )
                .order_by(GameCity.name, GameQuest.position)
            )).all()
            return [
                {
                    "id": row.quest_id,
                    "city_id": row.city_id,
                    "city_name": row.city_name,
                    "title": self._team_quest_title(row.translated_payload, row.payload, row.quest_id),
                }
                for row in rows
            ]

    @staticmethod
    def _team_quest_title(translated: dict | None, canonical: dict, fallback: str) -> str:
        for payload in (translated, canonical):
            if isinstance(payload, dict):
                scene = payload.get("scene")
                title = scene.get("title") if isinstance(scene, dict) else None
                if isinstance(title, str) and title.strip():
                    return title
        return fallback

    async def list_shared_quests(self, user_id: str, team_id: str, language: str = "ru") -> list[dict]:
        async with self.session_factory() as db:
            if await self._team_role(db, team_id, user_id) is None:
                raise SocialTeamNotFoundError
            quests = list((await db.scalars(
                select(SocialTeamQuest)
                .where(SocialTeamQuest.team_id == team_id)
                .order_by(SocialTeamQuest.created_at.desc())
            )).all())
            return [await self._shared_quest_payload(db, quest, language) for quest in quests]

    async def claim_shared_quest(
        self, user_id: str, team_id: str, shared_quest_id: str, language: str = "ru",
    ) -> dict:
        async with self.session_factory() as db:
            await self._lock_team(db, team_id)
            shared_quest = await db.scalar(
                select(SocialTeamQuest)
                .where(SocialTeamQuest.id == shared_quest_id, SocialTeamQuest.team_id == team_id)
                .with_for_update()
            )
            if shared_quest is None or await self._team_role(db, team_id, user_id) is None:
                raise SocialTeamNotFoundError
            is_participant = await db.get(SocialTeamQuestParticipant, (shared_quest_id, user_id))
            if is_participant is None:
                raise SocialTeamPermissionError
            if shared_quest.status == "complete":
                payload = await self._shared_quest_payload(db, shared_quest, language)
                payload["xp_awarded"] = 0
                payload["rewards_credited"] = 0
                await db.commit()
                return payload

            payload = await self._shared_quest_payload(db, shared_quest, language)
            if not payload["ready_to_claim"]:
                payload["xp_awarded"] = 0
                payload["rewards_credited"] = 0
                await db.commit()
                return payload

            now = self._clock()
            shared_quest.status = "complete"
            shared_quest.completed_at = now
            participants = list((await db.scalars(
                select(SocialTeamQuestParticipant.user_id).where(
                    SocialTeamQuestParticipant.team_quest_id == shared_quest_id
                )
            )).all())
            caller_reward = 0
            rewards_credited = 0
            for participant_id in participants:
                awarded = await self.game_progress.award_shared_quest_bonus(
                    db,
                    participant_id,
                    shared_quest.quest_id,
                    shared_quest.reward_xp,
                    now,
                )
                if participant_id == user_id:
                    caller_reward = awarded
                if awarded:
                    rewards_credited += 1
            await db.commit()
            payload = await self._shared_quest_payload(db, shared_quest, language)
            payload["xp_awarded"] = caller_reward
            payload["rewards_credited"] = rewards_credited
            return payload

    async def get_weekly_league(self, user_id: str) -> dict:
        now = self._clock()
        week = league_week(now)
        async with self.session_factory() as db:
            await self._close_expired_leagues(db, now)
            await self._ensure_league_season(db, week)
            previous_row = (await db.execute(
                select(
                    LeagueSeason.id,
                    LeagueSeason.closed_at,
                    LeagueMembership.weekly_xp,
                    LeagueMembership.final_place,
                    LeagueMembership.rank,
                    LeagueMembership.final_rank,
                    LeagueMembership.movement,
                )
                .join(LeagueMembership, LeagueMembership.season_id == LeagueSeason.id)
                .where(
                    LeagueMembership.user_id == user_id,
                    LeagueSeason.status == "closed",
                    LeagueMembership.final_rank.is_not(None),
                )
                .order_by(LeagueSeason.ends_at.desc())
                .limit(1)
            )).one_or_none()
            previous_result = None if previous_row is None else {
                "season_id": previous_row.id,
                "weekly_xp": previous_row.weekly_xp,
                "place": previous_row.final_place,
                "rank_before": previous_row.rank,
                "rank_after": previous_row.final_rank,
                "movement": previous_row.movement,
                "closed_at": previous_row.closed_at.isoformat(),
            }
            membership = await db.get(LeagueMembership, (week.season_id, user_id))
            if membership is None:
                await db.commit()
                return {
                    "joined": False,
                    "season_id": week.season_id,
                    "starts_at": week.starts_at.isoformat(),
                    "ends_at": week.ends_at.isoformat(),
                    "previous_result": previous_result,
                    "members": [],
                }

            memberships = list((await db.scalars(
                select(LeagueMembership).where(LeagueMembership.season_id == week.season_id)
            )).all())
            score_by_user = await self._league_scores(db, week, [row.user_id for row in memberships])
            current_scores = [
                LeagueScore(row.user_id, score_by_user.get(row.user_id, 0), row.rank)
                for row in memberships
            ]
            settlement = {row.user_id: row for row in settle_weekly_ranks(current_scores)}

            first_direction = await db.execute(
                select(Friendship.user_b_id).where(Friendship.user_a_id == user_id)
            )
            second_direction = await db.execute(
                select(Friendship.user_a_id).where(Friendship.user_b_id == user_id)
            )
            visible_user_ids = {user_id, *first_direction.scalars().all(), *second_direction.scalars().all()}
            member_rows = (await db.execute(
                select(LeagueMembership, User.name)
                .join(User, User.id == LeagueMembership.user_id)
                .where(
                    LeagueMembership.season_id == week.season_id,
                    LeagueMembership.user_id.in_(visible_user_ids),
                )
            )).all()
            members = []
            for row, name in member_rows:
                settled = settlement[row.user_id]
                members.append({
                    "user_id": row.user_id,
                    "name": name,
                    "rank": row.rank,
                    "place": settled.place,
                    "weekly_xp": settled.weekly_xp,
                    "projected_rank": settled.rank_after,
                    "projected_movement": settled.movement,
                    "is_self": row.user_id == user_id,
                })
            members.sort(key=lambda row: (row["rank"], row["place"], row["user_id"]))
            await db.commit()
            return {
                "joined": True,
                "season_id": week.season_id,
                "starts_at": week.starts_at.isoformat(),
                "ends_at": week.ends_at.isoformat(),
                "rank": membership.rank,
                "participant_count": len(memberships),
                "previous_result": previous_result,
                "members": members,
            }

    async def join_weekly_league(self, user_id: str) -> dict:
        now = self._clock()
        week = league_week(now)
        async with self.session_factory() as db:
            await self._close_expired_leagues(db, now)
            await self._ensure_league_season(db, week)
            existing = await db.get(LeagueMembership, (week.season_id, user_id))
            if existing is None:
                previous_rank = await db.scalar(
                    select(LeagueMembership.final_rank)
                    .join(LeagueSeason, LeagueSeason.id == LeagueMembership.season_id)
                    .where(
                        LeagueMembership.user_id == user_id,
                        LeagueSeason.status == "closed",
                        LeagueMembership.final_rank.is_not(None),
                    )
                    .order_by(LeagueSeason.ends_at.desc())
                    .limit(1)
                )
                await db.execute(
                    pg_insert(LeagueMembership)
                    .values(
                        season_id=week.season_id,
                        user_id=user_id,
                        rank=previous_rank or 1,
                        joined_at=now,
                        weekly_xp=0,
                    )
                    .on_conflict_do_nothing(index_elements=["season_id", "user_id"])
                )
            await db.commit()
        return await self.get_weekly_league(user_id)

    async def settle_expired_leagues(self) -> int:
        """Close expired league seasons; safe for periodic and concurrent callers."""
        async with self.session_factory() as db:
            closed_count = await self._close_expired_leagues(db, self._clock())
            await db.commit()
            return closed_count

    @staticmethod
    async def _ensure_league_season(db: AsyncSession, week: LeagueWeek) -> None:
        await db.execute(
            pg_insert(LeagueSeason)
            .values(
                id=week.season_id,
                starts_at=week.starts_at,
                ends_at=week.ends_at,
                status="open",
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )

    @staticmethod
    async def _league_scores(db: AsyncSession, week: LeagueWeek, user_ids: list[str]) -> dict[str, int]:
        if not user_ids:
            return {}
        rows = await db.execute(
            select(GameRewardLedger.user_id, func.sum(GameRewardLedger.xp))
            .where(
                GameRewardLedger.user_id.in_(user_ids),
                GameRewardLedger.awarded_at >= week.starts_at,
                GameRewardLedger.awarded_at < week.ends_at,
                GameRewardLedger.xp > 0,
            )
            .group_by(GameRewardLedger.user_id)
        )
        return {user_id: int(total or 0) for user_id, total in rows.all()}

    async def _close_expired_leagues(self, db: AsyncSession, now: datetime) -> int:
        seasons = list((await db.scalars(
            select(LeagueSeason)
            .where(LeagueSeason.status == "open", LeagueSeason.ends_at <= now)
            .order_by(LeagueSeason.ends_at)
            .with_for_update()
        )).all())
        closed_count = 0
        for season in seasons:
            memberships = list((await db.scalars(
                select(LeagueMembership)
                .where(LeagueMembership.season_id == season.id)
                .with_for_update()
            )).all())
            week = LeagueWeek(season.id, season.starts_at, season.ends_at)
            score_by_user = await self._league_scores(db, week, [row.user_id for row in memberships])
            outcomes = settle_weekly_ranks([
                LeagueScore(row.user_id, score_by_user.get(row.user_id, 0), row.rank)
                for row in memberships
            ])
            member_by_user = {row.user_id: row for row in memberships}
            for outcome in outcomes:
                row = member_by_user[outcome.user_id]
                row.weekly_xp = outcome.weekly_xp
                row.final_place = outcome.place
                row.final_rank = outcome.rank_after
                row.movement = outcome.movement
            season.status = "closed"
            season.closed_at = now
            closed_count += 1
        return closed_count

    @staticmethod
    async def _shared_quest_payload(
        db: AsyncSession, shared_quest: SocialTeamQuest, language: str = "ru",
    ) -> dict:
        participant_rows = (await db.execute(
            select(SocialTeamQuestParticipant.user_id, User.name)
            .join(User, User.id == SocialTeamQuestParticipant.user_id)
            .where(SocialTeamQuestParticipant.team_quest_id == shared_quest.id)
            .order_by(User.name)
        )).all()
        participant_ids = [row.user_id for row in participant_rows]
        completed_ids = set()
        if participant_ids:
            completed_ids = set((await db.scalars(
                select(GameQuestCompletion.user_id).where(
                    GameQuestCompletion.quest_id == shared_quest.quest_id,
                    GameQuestCompletion.user_id.in_(participant_ids),
                )
            )).all())
        participant_count = len(participant_rows)
        completed_count = len(completed_ids)
        payload_rows = await db.execute(
            select(GameContentRevision.payload, GameContentTranslation.payload)
            .join(GameQuest, GameQuest.content_revision_id == GameContentRevision.id)
            .outerjoin(
                GameContentTranslation,
                and_(
                    GameContentTranslation.content_revision_id == GameContentRevision.id,
                    GameContentTranslation.language == ("en" if language == "en" else "ru"),
                    GameContentTranslation.is_published.is_(True),
                ),
            )
            .where(GameQuest.id == shared_quest.quest_id)
        )
        canonical, translated = payload_rows.one()
        quest_title = SocialService._team_quest_title(translated, canonical, shared_quest.quest_id)
        return {
            "id": shared_quest.id,
            "quest_id": shared_quest.quest_id,
            "quest_title": quest_title,
            "status": shared_quest.status,
            "participant_count": participant_count,
            "completed_count": completed_count,
            "ready_to_claim": participant_count > 0 and completed_count == participant_count,
            "created_at": shared_quest.created_at.isoformat(),
            "completed_at": shared_quest.completed_at.isoformat() if shared_quest.completed_at else None,
            "participants": [
                {"id": row.user_id, "name": row.name, "completed": row.user_id in completed_ids}
                for row in participant_rows
            ],
        }

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
