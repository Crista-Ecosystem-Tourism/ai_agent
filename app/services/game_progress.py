from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.game import (
    GameAttempt,
    GameCity,
    GameContentRevision,
    GameDailyProgress,
    GameProfile,
    GameQuest,
    GameQuestCompletion,
    GameRewardLedger,
    GameStamp,
)


ONBOARDING_REVISION_ID = "onboarding-moscow-v1"
ONBOARDING_INTERACTION_KEY = "red-square-name"
STARTER_STAMP_KEY = "moscow-starter"
ONBOARDING_QUEST_ID = "moscow-red-square"
DAILY_ENERGY = 5
ONBOARDING_XP = 50
DAILY_GOAL_QUESTS = 2
GAME_TIMEZONE = ZoneInfo("Europe/Moscow")


class GameContentUnavailableError(RuntimeError):
    pass


class GameQuestLockedError(RuntimeError):
    pass


class GameProgressService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_onboarding(self, user_id: str) -> dict[str, Any]:
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            content = await self._published_content(db)
            stamp = await self._backfill_onboarding_completion(db, user_id)
            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()
            return {
                "content": self._public_content(content.payload),
                "profile": self._profile_payload(profile),
                "daily": daily,
                "completed": stamp is not None,
                "starter_stamp": self._stamp_payload(stamp),
            }

    async def answer_red_square(self, user_id: str, answer_key: str) -> dict[str, Any]:
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            content = await self._published_content(db)
            question = content.payload.get("question", {})
            options = question.get("options", [])
            allowed_answers = {option.get("id") for option in options}
            if answer_key not in allowed_answers:
                raise ValueError("Unknown answer option")

            is_correct = answer_key == question.get("correct_option_id")
            now = datetime.now(timezone.utc)
            db.add(GameAttempt(
                id=uuid.uuid4().hex,
                user_id=user_id,
                content_revision_id=content.id,
                interaction_key=ONBOARDING_INTERACTION_KEY,
                answer_key=answer_key,
                is_correct=is_correct,
                created_at=now,
            ))

            xp_awarded = 0
            stamp: GameStamp | None = None
            if is_correct:
                # The unique stamp is the reward ledger. INSERT .. ON CONFLICT
                # makes retries and concurrent requests idempotent.
                result = await db.execute(
                    pg_insert(GameStamp)
                    .values(
                        id=uuid.uuid4().hex,
                        user_id=user_id,
                        stamp_key=STARTER_STAMP_KEY,
                        content_revision_id=content.id,
                        title="Стартовый штамп — Москва",
                        earned_at=now,
                    )
                    .on_conflict_do_nothing(constraint="uq_game_stamp_user_key")
                    .returning(GameStamp.id)
                )
                stamp_id = result.scalar_one_or_none()
                if stamp_id:
                    xp_awarded = await self._record_reward(
                        db, user_id, ONBOARDING_QUEST_ID, STARTER_STAMP_KEY, ONBOARDING_XP, now,
                    )
                    profile.xp += xp_awarded
                    await self._record_daily_completion(db, profile, user_id, now)
                    profile.updated_at = now
                stamp = await db.scalar(
                    select(GameStamp).where(
                        GameStamp.user_id == user_id,
                        GameStamp.stamp_key == STARTER_STAMP_KEY,
                    )
                )
                await self._record_onboarding_completion(db, user_id, now)
            else:
                profile.energy = max(0, profile.energy - 1)
                profile.updated_at = now

            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()
            return {
                "correct": is_correct,
                "xp_awarded": xp_awarded,
                "profile": self._profile_payload(profile),
                "daily": daily,
                "completed": stamp is not None,
                "starter_stamp": self._stamp_payload(stamp),
            }

    async def get_moscow_path(self, user_id: str) -> dict[str, Any]:
        """Return only published nodes and calculate unlocks from server completions."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)

            city = await db.scalar(
                select(GameCity).where(GameCity.id == "moscow", GameCity.is_published.is_(True))
            )
            if city is None:
                raise GameContentUnavailableError("Moscow path is not published")
            quests = list((await db.scalars(
                select(GameQuest)
                .where(GameQuest.city_id == city.id, GameQuest.is_published.is_(True))
                .order_by(GameQuest.position)
            )).all())
            completed_ids = set((await db.scalars(
                select(GameQuestCompletion.quest_id).where(GameQuestCompletion.user_id == user_id)
            )).all())
            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()

            nodes = []
            for quest in quests:
                completed = quest.id in completed_ids
                nodes.append({
                    "id": quest.id,
                    "kind": quest.kind,
                    "position": quest.position,
                    "completed": completed,
                    "unlocked": (
                        quest.prerequisite_quest_id is None
                        or quest.prerequisite_quest_id in completed_ids
                    ),
                    "prerequisite_quest_id": quest.prerequisite_quest_id,
                })
            return {
                "city": {"id": city.id, "name": city.name, "tier": city.tier},
                "profile": self._profile_payload(profile),
                "daily": daily,
                "nodes": nodes,
            }

    async def get_moscow_quest(self, user_id: str, quest_id: str) -> dict[str, Any]:
        """Return a published Moscow lesson only when its server prerequisite is met."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            quest, content = await self._published_moscow_quest(db, quest_id)
            await self._ensure_quest_unlocked(db, user_id, quest)
            completed = await db.get(GameQuestCompletion, (user_id, quest.id))
            stamp = await self._quest_stamp(db, user_id, content)
            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()
            return {
                "quest": self._quest_payload(quest),
                "content": self._public_content(content.payload),
                "profile": self._profile_payload(profile),
                "daily": daily,
                "completed": completed is not None,
                "stamp": self._stamp_payload(stamp),
            }

    async def answer_moscow_quest(
        self, user_id: str, quest_id: str, answer_key: str,
    ) -> dict[str, Any]:
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            quest, content = await self._published_moscow_quest(db, quest_id)
            await self._ensure_quest_unlocked(db, user_id, quest)

            question = content.payload.get("question", {})
            options = question.get("options", [])
            allowed_answers = {option.get("id") for option in options}
            if answer_key not in allowed_answers:
                raise ValueError("Unknown answer option")

            is_correct = answer_key == question.get("correct_option_id")
            now = datetime.now(timezone.utc)
            db.add(GameAttempt(
                id=uuid.uuid4().hex,
                user_id=user_id,
                content_revision_id=content.id,
                interaction_key=str(question.get("id", quest.id)),
                answer_key=answer_key,
                is_correct=is_correct,
                created_at=now,
            ))

            xp_awarded = 0
            stamp: GameStamp | None = None
            if is_correct:
                reward = content.payload.get("reward", {})
                stamp_key = reward.get("stamp_key")
                stamp_title = reward.get("stamp_title")
                if not isinstance(stamp_key, str) or not isinstance(stamp_title, str):
                    raise GameContentUnavailableError("Quest reward is not configured")
                result = await db.execute(
                    pg_insert(GameStamp)
                    .values(
                        id=uuid.uuid4().hex,
                        user_id=user_id,
                        stamp_key=stamp_key,
                        content_revision_id=content.id,
                        title=stamp_title,
                        earned_at=now,
                    )
                    .on_conflict_do_nothing(constraint="uq_game_stamp_user_key")
                    .returning(GameStamp.id)
                )
                stamp_id = result.scalar_one_or_none()
                if stamp_id:
                    xp_awarded = await self._record_reward(
                        db, user_id, quest.id, stamp_key, int(reward.get("xp", 0)), now,
                    )
                    profile.xp += xp_awarded
                    await self._record_daily_completion(db, profile, user_id, now)
                    profile.updated_at = now
                stamp = await self._quest_stamp(db, user_id, content)
                await self._record_quest_completion(db, user_id, quest.id, now)
            else:
                profile.energy = max(0, profile.energy - 1)
                profile.updated_at = now

            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()
            return {
                "correct": is_correct,
                "xp_awarded": xp_awarded,
                "profile": self._profile_payload(profile),
                "daily": daily,
                "completed": stamp is not None,
                "stamp": self._stamp_payload(stamp),
            }

    async def _ensure_profile(self, db: AsyncSession, user_id: str) -> GameProfile:
        today = datetime.now(GAME_TIMEZONE).date()
        profile = await db.get(GameProfile, user_id)
        if profile is None:
            profile = GameProfile(
                user_id=user_id,
                xp=0,
                energy=DAILY_ENERGY,
                energy_refreshed_on=today,
                streak=0,
            )
            db.add(profile)
            await db.flush()
        elif profile.energy_refreshed_on < today:
            profile.energy = DAILY_ENERGY
            profile.energy_refreshed_on = today
            profile.updated_at = datetime.now(timezone.utc)
        return profile

    @staticmethod
    async def _record_reward(
        db: AsyncSession,
        user_id: str,
        quest_id: str,
        reward_key: str,
        xp: int,
        awarded_at: datetime,
    ) -> int:
        result = await db.execute(
            pg_insert(GameRewardLedger)
            .values(
                id=uuid.uuid4().hex,
                user_id=user_id,
                quest_id=quest_id,
                reward_key=reward_key,
                xp=xp,
                awarded_at=awarded_at,
            )
            .on_conflict_do_nothing(constraint="uq_game_reward_user_key")
            .returning(GameRewardLedger.id)
        )
        return xp if result.scalar_one_or_none() else 0

    @staticmethod
    async def _record_daily_completion(
        db: AsyncSession, profile: GameProfile, user_id: str, completed_at: datetime,
    ) -> None:
        activity_date = completed_at.astimezone(GAME_TIMEZONE).date()
        if profile.last_activity_on != activity_date:
            profile.streak = (
                profile.streak + 1
                if profile.last_activity_on == activity_date - timedelta(days=1)
                else 1
            )
            profile.last_activity_on = activity_date

        daily = await db.get(GameDailyProgress, (user_id, activity_date))
        if daily is None:
            daily = GameDailyProgress(
                user_id=user_id,
                goal_date=activity_date,
                completed_quests=0,
            )
            db.add(daily)
        daily.completed_quests += 1
        if daily.completed_quests >= DAILY_GOAL_QUESTS and daily.goal_reached_at is None:
            daily.goal_reached_at = completed_at

    @staticmethod
    async def _daily_payload(
        db: AsyncSession, user_id: str, profile: GameProfile,
    ) -> dict[str, Any]:
        today = datetime.now(GAME_TIMEZONE).date()
        daily = await db.get(GameDailyProgress, (user_id, today))
        completed = daily.completed_quests if daily is not None else 0
        return {
            "timezone": "Europe/Moscow",
            "streak": profile.streak,
            "completed_quests": completed,
            "goal": DAILY_GOAL_QUESTS,
            "goal_reached": daily is not None and daily.goal_reached_at is not None,
        }

    async def _published_content(self, db: AsyncSession) -> GameContentRevision:
        content = await db.scalar(
            select(GameContentRevision).where(
                GameContentRevision.id == ONBOARDING_REVISION_ID,
                GameContentRevision.is_published.is_(True),
            )
        )
        if content is None:
            raise GameContentUnavailableError("Onboarding content is not published")
        return content

    @staticmethod
    async def _backfill_onboarding_completion(
        db: AsyncSession, user_id: str,
    ) -> GameStamp | None:
        """Keep accounts completed before quest paths were introduced on the path."""
        stamp = await db.scalar(
            select(GameStamp).where(
                GameStamp.user_id == user_id,
                GameStamp.stamp_key == STARTER_STAMP_KEY,
            )
        )
        if stamp is not None:
            await GameProgressService._record_onboarding_completion(db, user_id, stamp.earned_at)
        return stamp

    async def _published_moscow_quest(
        self, db: AsyncSession, quest_id: str,
    ) -> tuple[GameQuest, GameContentRevision]:
        quest = await db.scalar(
            select(GameQuest)
            .join(GameCity, GameQuest.city_id == GameCity.id)
            .where(
                GameQuest.id == quest_id,
                GameQuest.is_published.is_(True),
                GameCity.id == "moscow",
                GameCity.is_published.is_(True),
            )
        )
        if quest is None:
            raise GameContentUnavailableError("Moscow quest is not published")
        content = await db.scalar(
            select(GameContentRevision).where(
                GameContentRevision.id == quest.content_revision_id,
                GameContentRevision.is_published.is_(True),
            )
        )
        if content is None:
            raise GameContentUnavailableError("Moscow quest content is not published")
        return quest, content

    @staticmethod
    async def _ensure_quest_unlocked(
        db: AsyncSession, user_id: str, quest: GameQuest,
    ) -> None:
        if quest.prerequisite_quest_id is None:
            return
        completion = await db.get(
            GameQuestCompletion, (user_id, quest.prerequisite_quest_id),
        )
        if completion is None:
            raise GameQuestLockedError("Complete the prerequisite quest first")

    @staticmethod
    async def _record_onboarding_completion(
        db: AsyncSession, user_id: str, completed_at: datetime,
    ) -> None:
        await db.execute(
            pg_insert(GameQuestCompletion)
            .values(
                user_id=user_id,
                quest_id=ONBOARDING_QUEST_ID,
                completed_at=completed_at,
            )
            .on_conflict_do_nothing(
                constraint="pk_game_quest_completion"
            )
        )

    @staticmethod
    async def _record_quest_completion(
        db: AsyncSession, user_id: str, quest_id: str, completed_at: datetime,
    ) -> None:
        await db.execute(
            pg_insert(GameQuestCompletion)
            .values(user_id=user_id, quest_id=quest_id, completed_at=completed_at)
            .on_conflict_do_nothing(constraint="pk_game_quest_completion")
        )

    @staticmethod
    def _public_content(payload: dict[str, Any]) -> dict[str, Any]:
        question = dict(payload.get("question", {}))
        question.pop("correct_option_id", None)
        return {**payload, "question": question}

    @staticmethod
    def _profile_payload(profile: GameProfile) -> dict[str, Any]:
        return {"xp": profile.xp, "energy": profile.energy, "streak": profile.streak}

    @staticmethod
    def _quest_payload(quest: GameQuest) -> dict[str, Any]:
        return {
            "id": quest.id,
            "kind": quest.kind,
            "position": quest.position,
            "prerequisite_quest_id": quest.prerequisite_quest_id,
        }

    @staticmethod
    async def _quest_stamp(
        db: AsyncSession, user_id: str, content: GameContentRevision,
    ) -> GameStamp | None:
        stamp_key = content.payload.get("reward", {}).get("stamp_key")
        if not isinstance(stamp_key, str):
            return None
        return await db.scalar(
            select(GameStamp).where(
                GameStamp.user_id == user_id,
                GameStamp.stamp_key == stamp_key,
            )
        )

    @staticmethod
    def _stamp_payload(stamp: GameStamp | None) -> dict[str, Any] | None:
        if stamp is None:
            return None
        return {"key": stamp.stamp_key, "title": stamp.title, "earned_at": stamp.earned_at}
