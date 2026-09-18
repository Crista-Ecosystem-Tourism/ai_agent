import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Register all relationship targets before configuring SQLAlchemy mappers.
from app.db.models import chat  # noqa: F401
from app.db.models.auth import User
from app.services.game_progress import GameProgressService, GameQuestLockedError
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
        self.assertEqual(initial["profile"], {"xp": 0, "energy": 5, "streak": 0})
        self.assertEqual(initial["daily"], {
            "timezone": "Europe/Moscow", "streak": 0, "completed_quests": 0,
            "goal": 2, "goal_reached": False,
        })
        self.assertNotIn("correct_option_id", initial["content"]["question"])
        initial_path = await self.game.get_moscow_path(self.user_id)
        self.assertEqual(initial_path["city"], {
            "id": "moscow", "name": "Москва", "tier": 1,
            "required_quest_count": 10,
            "completion_stamp": {
                "key": "moscow-city-explorer", "title": "Штамп «Москва: городской круг»",
            },
        })
        self.assertEqual(
            [node["id"] for node in initial_path["nodes"]],
            [
                "moscow-red-square", "moscow-spasskaya-tower", "moscow-tsar-bell",
                "moscow-annunciation-cathedral", "moscow-gum", "moscow-zaryadye",
                "moscow-tretyakov-gallery", "moscow-bolshoi-theatre", "moscow-metro", "moscow-vdnh",
            ],
        )
        self.assertEqual(
            [node["district"]["id"] for node in initial_path["nodes"]],
            [
                "moscow-kremlin", "moscow-kremlin", "moscow-kremlin", "moscow-kremlin",
                "moscow-kitaigorod", "moscow-kitaigorod", "moscow-zamoskvorechye",
                "moscow-teatralny", "moscow-teatralny", "moscow-vdnh",
            ],
        )
        self.assertTrue(initial_path["nodes"][0]["unlocked"])
        self.assertFalse(any(node["unlocked"] for node in initial_path["nodes"][1:]))

        with self.assertRaises(GameQuestLockedError):
            await self.game.get_moscow_quest(self.user_id, "moscow-spasskaya-tower")
        with self.assertRaises(GameQuestLockedError):
            await self.game.answer_moscow_quest(self.user_id, "moscow-spasskaya-tower", "1491")
        with self.assertRaises(GameQuestLockedError):
            await self.game.get_moscow_boss(self.user_id)

        incorrect = await self.game.answer_red_square(self.user_id, "color")
        self.assertFalse(incorrect["correct"])
        self.assertEqual(incorrect["profile"], {"xp": 0, "energy": 4, "streak": 0})
        self.assertEqual(incorrect["xp_awarded"], 0)

        correct = await self.game.answer_red_square(self.user_id, "beautiful")
        self.assertTrue(correct["correct"])
        self.assertEqual(correct["xp_awarded"], 50)
        self.assertEqual(correct["profile"], {"xp": 50, "energy": 4, "streak": 1})
        self.assertEqual(correct["daily"]["completed_quests"], 1)
        self.assertFalse(correct["daily"]["goal_reached"])
        self.assertTrue(correct["completed"])
        self.assertEqual(correct["starter_stamp"]["key"], "moscow-starter")

        completed_path = await self.game.get_moscow_path(self.user_id)
        self.assertTrue(completed_path["nodes"][0]["completed"])
        self.assertTrue(completed_path["nodes"][1]["unlocked"])
        self.assertFalse(completed_path["nodes"][2]["unlocked"])

        second = await self.game.get_moscow_quest(self.user_id, "moscow-spasskaya-tower")
        self.assertEqual(second["quest"]["prerequisite_quest_id"], "moscow-red-square")
        self.assertNotIn("correct_option_id", second["content"]["question"])

        second_incorrect = await self.game.answer_moscow_quest(
            self.user_id, "moscow-spasskaya-tower", "1547"
        )
        self.assertFalse(second_incorrect["correct"])
        self.assertEqual(second_incorrect["profile"], {"xp": 50, "energy": 3, "streak": 1})

        second_correct = await self.game.answer_moscow_quest(
            self.user_id, "moscow-spasskaya-tower", "1491"
        )
        self.assertTrue(second_correct["correct"])
        self.assertEqual(second_correct["xp_awarded"], 25)
        self.assertEqual(second_correct["profile"], {"xp": 75, "energy": 3, "streak": 1})
        self.assertEqual(second_correct["stamp"]["key"], "moscow-spasskaya")
        self.assertEqual(second_correct["daily"]["completed_quests"], 2)
        self.assertTrue(second_correct["daily"]["goal_reached"])

        third = await self.game.get_moscow_quest(self.user_id, "moscow-tsar-bell")
        self.assertEqual(third["quest"]["prerequisite_quest_id"], "moscow-spasskaya-tower")
        self.assertNotIn("correct_option_id", third["content"]["question"])
        third_correct = await self.game.answer_moscow_quest(
            self.user_id, "moscow-tsar-bell", "1735"
        )
        self.assertTrue(third_correct["correct"])
        self.assertEqual(third_correct["xp_awarded"], 25)
        self.assertEqual(third_correct["profile"], {"xp": 100, "energy": 3, "streak": 1})
        self.assertEqual(third_correct["daily"]["completed_quests"], 3)
        self.assertEqual(third_correct["stamp"]["key"], "moscow-tsar-bell")

        second_retry = await self.game.answer_moscow_quest(
            self.user_id, "moscow-spasskaya-tower", "1491"
        )
        self.assertEqual(second_retry["xp_awarded"], 0)
        self.assertEqual(second_retry["profile"], {"xp": 100, "energy": 3, "streak": 1})

        retry = await self.game.answer_red_square(self.user_id, "beautiful")
        self.assertEqual(retry["xp_awarded"], 0)
        self.assertEqual(retry["profile"], {"xp": 100, "energy": 3, "streak": 1})

        tier_one_answers = [
            ("moscow-annunciation-cathedral", "1489"),
            ("moscow-gum", "1893"),
            ("moscow-zaryadye", "2017"),
            ("moscow-tretyakov-gallery", "1856"),
            ("moscow-bolshoi-theatre", "1825"),
            ("moscow-metro", "1935"),
            ("moscow-vdnh", "1939"),
        ]
        for quest_id, answer_key in tier_one_answers:
            result = await self.game.answer_moscow_quest(self.user_id, quest_id, answer_key)
            self.assertTrue(result["correct"])
            self.assertEqual(result["xp_awarded"], 25)

        completed_city_path = await self.game.get_moscow_path(self.user_id)
        self.assertTrue(all(node["completed"] for node in completed_city_path["nodes"]))
        self.assertEqual(completed_city_path["profile"]["xp"], 275)
        self.assertEqual(completed_city_path["boss"], {
            "title": "Финальный круг Москвы",
            "question_count": 3,
            "unlocked": True,
            "completed": False,
            "sandbox_unlocked": False,
        })

        boss = await self.game.get_moscow_boss(self.user_id)
        self.assertEqual(boss["city"], {"id": "moscow", "name": "Москва"})
        self.assertEqual(len(boss["content"]["questions"]), 3)
        self.assertTrue(all(
            "correct_option_id" not in question
            for question in boss["content"]["questions"]
        ))

        boss_incorrect = await self.game.answer_moscow_boss(self.user_id, [
            {"question_id": "moscow-boss-cathedral", "answer_key": "1561"},
            {"question_id": "moscow-boss-gum", "answer_key": "1893"},
            {"question_id": "moscow-boss-vdnh", "answer_key": "1939"},
        ])
        self.assertFalse(boss_incorrect["correct"])
        self.assertEqual(boss_incorrect["incorrect_answers"], 1)
        self.assertFalse(boss_incorrect["completed"])
        self.assertEqual(boss_incorrect["profile"], {"xp": 275, "energy": 2, "streak": 1})

        boss_correct = await self.game.answer_moscow_boss(self.user_id, [
            {"question_id": "moscow-boss-cathedral", "answer_key": "1489"},
            {"question_id": "moscow-boss-gum", "answer_key": "1893"},
            {"question_id": "moscow-boss-vdnh", "answer_key": "1939"},
        ])
        self.assertTrue(boss_correct["correct"])
        self.assertTrue(boss_correct["completed"])
        self.assertTrue(boss_correct["sandbox_unlocked"])
        self.assertEqual(boss_correct["city_stamp"]["key"], "moscow-city-explorer")
        self.assertEqual(boss_correct["profile"], {"xp": 275, "energy": 2, "streak": 1})

        boss_retry = await self.game.answer_moscow_boss(self.user_id, [
            {"question_id": "moscow-boss-cathedral", "answer_key": "1489"},
            {"question_id": "moscow-boss-gum", "answer_key": "1893"},
            {"question_id": "moscow-boss-vdnh", "answer_key": "1939"},
        ])
        self.assertTrue(boss_retry["completed"])
        self.assertEqual(boss_retry["profile"], {"xp": 275, "energy": 2, "streak": 1})
        self.assertEqual((await self.game.get_moscow_path(self.user_id))["boss"]["sandbox_unlocked"], True)
