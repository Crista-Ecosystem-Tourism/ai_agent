import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Register relationship targets before SQLAlchemy configures User mappings.
from app.db.models import chat  # noqa: F401
from app.db.dsn import get_database_url
from app.db.models.auth import User
from app.db.models.game import GameProfile, GameRewardLedger
from app.db.models.social import Friendship
from app.core.social_tokens import canonical_friend_pair, shared_quest_reward_key
from app.services.game_progress import GameProgressService
from app.services.social import SocialService


class SocialTeamQuestIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Runs against an already-migrated disposable PostgreSQL database."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(get_database_url())
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.owner_id = uuid.uuid4().hex
        self.member_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add_all([
                User(id=self.owner_id, email=f"social-owner-{self.owner_id}@example.test", name="Owner", is_active=True, auth_provider="test", created_at=now, updated_at=now),
                User(id=self.member_id, email=f"social-member-{self.member_id}@example.test", name="Member", is_active=True, auth_provider="test", created_at=now, updated_at=now),
            ])
            user_a_id, user_b_id = canonical_friend_pair(self.owner_id, self.member_id)
            db.add(Friendship(user_a_id=user_a_id, user_b_id=user_b_id, created_at=now))
            await db.commit()
        self.game = GameProgressService(self.sessions)
        self.social = SocialService(self.sessions, self.game)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_shared_quest_credits_each_participant_once(self):
        team = await self.social.create_team(self.owner_id, "Test team")
        await self.social.add_team_member(self.owner_id, team["id"], self.member_id)
        shared = await self.social.create_shared_quest(self.owner_id, team["id"], "moscow-red-square")
        self.assertEqual(shared["participant_count"], 2)

        first = await self.game.answer_city_quest(self.owner_id, "moscow", "moscow-red-square", "beautiful")
        second = await self.game.answer_city_quest(self.member_id, "moscow", "moscow-red-square", "beautiful")
        self.assertTrue(first["correct"])
        self.assertTrue(second["correct"])

        settled = await self.social.claim_shared_quest(self.owner_id, team["id"], shared["id"])
        self.assertEqual(settled["status"], "complete")
        self.assertEqual(settled["completed_count"], 2)
        self.assertGreater(settled["xp_awarded"], 0)

        replay = await self.social.claim_shared_quest(self.member_id, team["id"], shared["id"])
        self.assertEqual(replay["status"], "complete")
        self.assertEqual(replay["xp_awarded"], 0)

        second_team = await self.social.create_team(self.owner_id, "Second test team")
        await self.social.add_team_member(self.owner_id, second_team["id"], self.member_id)
        second_shared = await self.social.create_shared_quest(
            self.owner_id, second_team["id"], "moscow-red-square",
        )
        second_settlement = await self.social.claim_shared_quest(
            self.member_id, second_team["id"], second_shared["id"],
        )
        self.assertEqual(second_settlement["status"], "complete")
        self.assertEqual(second_settlement["xp_awarded"], 0)

        reward_key = shared_quest_reward_key("moscow-red-square")
        async with self.sessions() as db:
            for user_id in (self.owner_id, self.member_id):
                receipts = list((await db.scalars(select(GameRewardLedger).where(
                    GameRewardLedger.user_id == user_id,
                    GameRewardLedger.reward_key == reward_key,
                ))).all())
                profile = await db.get(GameProfile, user_id)
                self.assertEqual(len(receipts), 1)
                solo_xp = first["xp_awarded"] if user_id == self.owner_id else second["xp_awarded"]
                self.assertEqual(profile.xp, solo_xp + settled["xp_awarded"])


if __name__ == "__main__":
    unittest.main()
