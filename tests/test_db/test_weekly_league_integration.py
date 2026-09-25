import uuid
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.social_tokens import canonical_friend_pair
from app.db.dsn import get_database_url
from app.db.models.auth import User
from app.db.models.game import GameRewardLedger
from app.db.models.social import Friendship, LeagueMembership, LeagueSeason
from app.services.game_progress import GameProgressService
from app.services.social import SocialService


class WeeklyLeagueIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Runs against an already-migrated disposable PostgreSQL database."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(get_database_url())
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime(2026, 9, 21, 12, tzinfo=timezone.utc)
        self.user_ids = [uuid.uuid4().hex for _ in range(6)]
        async with self.sessions() as db:
            db.add_all([
                User(
                    id=user_id,
                    email=f"league-{user_id}@example.test",
                    name=f"Traveler {index}",
                    is_active=True,
                    auth_provider="test",
                    created_at=self.now,
                    updated_at=self.now,
                )
                for index, user_id in enumerate(self.user_ids)
            ])
            for friend_id in self.user_ids[1:5]:
                a_id, b_id = canonical_friend_pair(self.user_ids[0], friend_id)
                db.add(Friendship(user_a_id=a_id, user_b_id=b_id, created_at=self.now))
            await db.commit()
        self.game = GameProgressService(self.sessions)
        self.social = SocialService(self.sessions, self.game, clock=lambda: self.now)

    async def asyncTearDown(self):
        async with self.sessions() as db:
            await db.execute(Friendship.__table__.delete().where(
                Friendship.user_a_id.in_(self.user_ids) | Friendship.user_b_id.in_(self.user_ids)
            ))
            await db.execute(GameRewardLedger.__table__.delete().where(GameRewardLedger.user_id.in_(self.user_ids)))
            await db.execute(LeagueMembership.__table__.delete().where(LeagueMembership.user_id.in_(self.user_ids)))
            await db.execute(User.__table__.delete().where(User.id.in_(self.user_ids)))
            await db.commit()
        await self.engine.dispose()

    async def test_friends_league_scores_only_server_xp_and_closes_once(self):
        for user_id in self.user_ids:
            joined = await self.social.join_weekly_league(user_id)
            self.assertTrue(joined["joined"])

        async with self.sessions() as db:
            db.add_all([
                GameRewardLedger(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    quest_id="moscow-red-square",
                    reward_key=f"league-test:{user_id}",
                    xp=xp,
                    awarded_at=self.now + timedelta(hours=1),
                )
                for user_id, xp in zip(self.user_ids, (600, 500, 400, 300, 100, 50))
            ])
            await db.commit()

        view = await self.social.get_weekly_league(self.user_ids[0])
        self.assertEqual(6, view["participant_count"])
        self.assertEqual(5, len(view["members"]))  # Self plus accepted friends; outsider is hidden.
        self.assertEqual(600, next(row["weekly_xp"] for row in view["members"] if row["is_self"]))

        season_id = view["season_id"]
        self.now += timedelta(days=7)
        self.assertEqual(1, await self.social.settle_expired_leagues())
        async with self.sessions() as db:
            season = await db.get(LeagueSeason, season_id)
            top = await db.get(LeagueMembership, (season_id, self.user_ids[0]))
            self.assertEqual("closed", season.status)
            self.assertEqual(2, top.final_rank)
            first_closed_at = season.closed_at

        self.assertEqual(0, await self.social.settle_expired_leagues())
        async with self.sessions() as db:
            season = await db.get(LeagueSeason, season_id)
            self.assertEqual(first_closed_at, season.closed_at)
            self.assertEqual(1, await db.scalar(
                select(func.count()).select_from(LeagueSeason).where(
                    LeagueSeason.id == season_id, LeagueSeason.status == "closed",
                )
            ))

        next_week = await self.social.get_weekly_league(self.user_ids[0])
        self.assertFalse(next_week["joined"])
        self.assertEqual({
            "season_id": season_id,
            "weekly_xp": 600,
            "place": 1,
            "rank_before": 1,
            "rank_after": 2,
            "movement": "promoted",
            "closed_at": self.now.isoformat(),
        }, next_week["previous_result"])
        friend_history = await self.social.get_weekly_league(self.user_ids[1])
        self.assertEqual(500, friend_history["previous_result"]["weekly_xp"])
        self.assertNotEqual(next_week["previous_result"], friend_history["previous_result"])
        joined_next_week = await self.social.join_weekly_league(self.user_ids[0])
        self.assertTrue(joined_next_week["joined"])
        self.assertEqual(2, joined_next_week["rank"])
        self.assertEqual(next_week["previous_result"], joined_next_week["previous_result"])


if __name__ == "__main__":
    unittest.main()
