import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Register all relationship targets before configuring SQLAlchemy mappers.
from app.db.models import chat  # noqa: F401
from app.db.models.auth import User
from app.services.game_progress import GameProgressService
from app.db.dsn import get_database_url


class GameOnboardingIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Runs against an already-migrated disposable Postgres database."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(get_database_url())
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.user_id = uuid.uuid4().hex
        async with self.sessions() as db:
            await db.execute(insert(User).values(
                id=self.user_id,
                email=f"game-{self.user_id}@example.test",
                name="Game smoke test",
                is_active=True,
                auth_provider="test",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ))
            await db.commit()
        self.game = GameProgressService(self.sessions)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_reward_is_server_owned_and_idempotent(self):
        initial = await self.game.get_onboarding(self.user_id)
        self.assertEqual(initial["profile"], {"xp": 0, "energy": 5})
        self.assertNotIn("correct_option_id", initial["content"]["question"])
        initial_path = await self.game.get_moscow_path(self.user_id)
        self.assertEqual(initial_path["nodes"], [{
            "id": "moscow-red-square",
            "kind": "onboarding",
            "position": 1,
            "completed": False,
            "unlocked": True,
        }])

        incorrect = await self.game.answer_red_square(self.user_id, "color")
        self.assertFalse(incorrect["correct"])
        self.assertEqual(incorrect["profile"], {"xp": 0, "energy": 4})
        self.assertEqual(incorrect["xp_awarded"], 0)

        correct = await self.game.answer_red_square(self.user_id, "beautiful")
        self.assertTrue(correct["correct"])
        self.assertEqual(correct["xp_awarded"], 50)
        self.assertEqual(correct["profile"], {"xp": 50, "energy": 4})
        self.assertTrue(correct["completed"])
        self.assertEqual(correct["starter_stamp"]["key"], "moscow-starter")

        completed_path = await self.game.get_moscow_path(self.user_id)
        self.assertTrue(completed_path["nodes"][0]["completed"])

        retry = await self.game.answer_red_square(self.user_id, "beautiful")
        self.assertEqual(retry["xp_awarded"], 0)
        self.assertEqual(retry["profile"], {"xp": 50, "energy": 4})
