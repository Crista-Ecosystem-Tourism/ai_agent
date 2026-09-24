import asyncio
import unittest
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Register all relationship targets before configuring SQLAlchemy mappers.
from app.db.models import chat  # noqa: F401
from app.db.models.auth import User
from app.db.models.saved_route import SavedRoute
from app.services.game_progress import GameProgressService, GameQuestLockedError
from app.services.wiki import WikiNotFoundError, WikiService
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
        self.wiki = WikiService(self.sessions)

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
        with self.assertRaises(GameQuestLockedError):
            await self.game.get_moscow_sandbox(self.user_id)

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

        passport = await self.game.get_passport(self.user_id)
        self.assertEqual(passport["profile"], correct["profile"])
        self.assertEqual(passport["stamps"][0]["key"], "moscow-starter")
        self.assertEqual(next(city for city in passport["cities"] if city["id"] == "moscow")["completed_quests"], 1)
        async with self.sessions() as db:
            db.add(SavedRoute(id="passport-route", user_id=self.user_id, name="Музеи", destination="Москва", places={}, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)))
            await db.commit()
        passport_with_route = await self.game.get_passport(self.user_id)
        self.assertEqual(passport_with_route["routes"][0]["destination"], "Москва")

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
        self.assertIn("1491", second_incorrect["explanation"])
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
        self.assertEqual(
            boss_incorrect["feedback"][0],
            {
                "question_id": "moscow-boss-cathedral",
                "correct": False,
                "explanation": "Собор построили в 1484–1489 годах и освятили в 1489 году.",
            },
        )

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
        sandbox = await self.game.get_moscow_sandbox(self.user_id)
        self.assertEqual(sandbox["city_stamp"]["key"], "moscow-city-explorer")
        self.assertEqual(len(sandbox["lessons"]), 10)
        self.assertEqual(sandbox["lessons"][0]["title"], "Красная площадь")
        self.assertNotIn("correct_option_id", sandbox["lessons"][0]["question"])
        self.assertEqual(sandbox["drill"]["title"], "Правда или миф")
        self.assertEqual(len(sandbox["drill"]["statements"]), 3)
        self.assertNotIn("correct_answer", sandbox["drill"]["statements"][0])
        self.assertEqual(sandbox["matching"]["title"], "Соедини эпохи")
        self.assertEqual(len(sandbox["matching"]["pairs"]), 3)
        self.assertNotIn("correct_choice_id", sandbox["matching"]["pairs"][0])
        self.assertEqual(sandbox["timeline"]["title"], "Собери хронологию")
        self.assertEqual(len(sandbox["timeline"]["items"]), 3)
        self.assertNotIn("correct_position", sandbox["timeline"]["items"][0])
        self.assertEqual(sandbox["word_blocks"]["title"], "Собери фразу")
        self.assertEqual(len(sandbox["word_blocks"]["blocks"]), 4)
        self.assertNotIn("expected_order", sandbox["word_blocks"])
        self.assertEqual(sandbox["price_slider"]["fact_date"], "15 мая 1935 года")
        self.assertNotIn("target", sandbox["price_slider"])
        self.assertEqual(sandbox["story"]["title"], "Сцена: Красная площадь")
        self.assertIn("иллюстрация", sandbox["story"]["media_credit"].lower())
        self.assertEqual(sandbox["wiki_reference"], {"slug": "moscow", "version_id": "wiki-moscow-v1"})
        self.assertEqual(
            {lesson["wiki_reference"]["version_id"] for lesson in sandbox["lessons"]},
            {"wiki-moscow-v1"},
        )
        self.assertEqual(sandbox["photo_scanner"]["title"], "Фото-сканер: Кремлёвская стена")
        self.assertEqual(len(sandbox["photo_scanner"]["hotspots"]), 3)
        self.assertNotIn("correct_hotspot_id", sandbox["photo_scanner"])

        truth_myth = await self.game.answer_moscow_truth_myth(
            self.user_id, "zaryadye-2017", "truth",
        )
        self.assertTrue(truth_myth["correct"])
        self.assertIn("2017", truth_myth["explanation"])
        self.assertEqual(truth_myth["profile"], {"xp": 275, "energy": 2, "streak": 1})

        matching = await self.game.answer_moscow_matching(self.user_id, [
            {"pair_id": "cathedral-year", "choice_id": "year-1489"},
            {"pair_id": "gum-year", "choice_id": "year-1893"},
            {"pair_id": "vdnh-year", "choice_id": "year-1939"},
        ])
        self.assertTrue(matching["correct"])
        self.assertEqual(matching["incorrect_pairs"], [])
        self.assertEqual(len(matching["feedback"]), 3)
        self.assertEqual(matching["profile"], {"xp": 275, "energy": 2, "streak": 1})

        timeline = await self.game.answer_moscow_timeline(self.user_id, [
            "gum-1893", "metro-1935", "vdnh-1939",
        ])
        self.assertTrue(timeline["correct"])
        self.assertEqual(len(timeline["feedback"]), 3)
        self.assertEqual(timeline["profile"], {"xp": 275, "energy": 2, "streak": 1})

        word_blocks = await self.game.answer_moscow_word_blocks(self.user_id, [
            "word-moscow", "word-dash", "word-capital", "word-russia",
        ])
        self.assertTrue(word_blocks["correct"])
        self.assertIn("Москва", word_blocks["explanation"])
        self.assertEqual(word_blocks["profile"], {"xp": 275, "energy": 2, "streak": 1})

        price_slider = await self.game.answer_moscow_price_slider(self.user_id, 50)
        self.assertTrue(price_slider["correct"])
        self.assertIn("50 копеек", price_slider["explanation"])
        self.assertEqual(price_slider["profile"], {"xp": 275, "energy": 2, "streak": 1})

        recovery = await self.game.restore_moscow_energy_from_practice(self.user_id)
        self.assertEqual(recovery["profile"], {"xp": 275, "energy": 3, "streak": 1})
        self.assertTrue(recovery["practice_recovery"]["used_today"])
        self.assertFalse(recovery["practice_recovery"]["available"])

        photo_scanner = await self.game.answer_moscow_photo_scanner(self.user_id, "wall-merlons")
        self.assertTrue(photo_scanner["correct"])
        self.assertEqual(photo_scanner["profile"], {"xp": 275, "energy": 3, "streak": 1})

    async def test_first_game_requests_share_one_profile(self):
        onboarding, path = await asyncio.gather(
            self.game.get_onboarding(self.user_id),
            self.game.get_moscow_path(self.user_id),
        )
        self.assertEqual(onboarding["profile"], {"xp": 0, "energy": 5, "streak": 0})
        self.assertEqual(path["profile"], onboarding["profile"])

    async def test_generic_city_path_contract_preserves_moscow_route(self):
        path = await self.game.get_city_path(self.user_id, "moscow")
        self.assertEqual(path["city"]["id"], "moscow")
        quest = await self.game.get_city_quest(self.user_id, "moscow", "moscow-red-square")
        self.assertEqual(quest["quest"]["id"], "moscow-red-square")
        st_petersburg = await self.game.get_city_path(self.user_id, "st-petersburg")
        self.assertEqual(st_petersburg["city"]["name"], "Санкт-Петербург")
        self.assertEqual(
            [node["id"] for node in st_petersburg["nodes"]],
            ["spb-hermitage", "spb-peterhof", "spb-collection", "spb-fountains", "spb-peterhof-history"],
        )
        english_lesson = await self.game.get_city_quest(
            self.user_id, "st-petersburg", "spb-hermitage", "en"
        )
        russian_lesson = await self.game.get_city_quest(
            self.user_id, "st-petersburg", "spb-hermitage", "ru"
        )
        self.assertEqual(english_lesson["content_language"], "en")
        self.assertEqual(english_lesson["content"]["scene"]["title"], "The Hermitage")
        self.assertIn("1764", english_lesson["content"]["fact"]["text"])
        self.assertEqual(english_lesson["content"]["fact"]["source_url"], "https://hermitagemuseum.org/about/facts_and_figures")
        self.assertEqual(
            [option["id"] for option in english_lesson["content"]["question"]["options"]],
            ["1703", "1764", "1917"],
        )
        self.assertNotIn("correct_option_id", english_lesson["content"]["question"])
        self.assertEqual(russian_lesson["content_language"], "ru")
        self.assertEqual(russian_lesson["content"]["scene"]["title"], "Эрмитаж")
        first = await self.game.answer_city_quest(
            self.user_id, "st-petersburg", "spb-hermitage", "1764", "en"
        )
        self.assertEqual(first["xp_awarded"], 25)
        self.assertIn("The Hermitage dates", first["explanation"])
        second = await self.game.get_city_quest(self.user_id, "st-petersburg", "spb-peterhof")
        self.assertEqual(second["quest"]["id"], "spb-peterhof")
        sochi = await self.game.get_city_path(self.user_id, "sochi")
        self.assertEqual(
            [node["id"] for node in sochi["nodes"]],
            ["sochi-national-park", "sochi-dendrarium", "sochi-forest", "sochi-mzymta", "sochi-park-area"],
        )

    async def test_concurrent_correct_onboarding_awards_once(self):
        """Two devices may submit the same correct answer, but earn one reward."""
        first, second = await asyncio.gather(
            self.game.answer_red_square(self.user_id, "beautiful"),
            self.game.answer_red_square(self.user_id, "beautiful"),
        )
        self.assertEqual(sorted([first["xp_awarded"], second["xp_awarded"]]), [0, 50])
        self.assertTrue(first["completed"])
        self.assertTrue(second["completed"])

        profile = await self.game.get_onboarding(self.user_id)
        self.assertEqual(profile["profile"], {"xp": 50, "energy": 5, "streak": 1})
        self.assertEqual(profile["daily"]["completed_quests"], 1)

    async def test_moscow_day_boundary_refreshes_energy_and_resets_broken_streak(self):
        clock = [datetime(2026, 9, 1, 20, 59, tzinfo=timezone.utc)]  # 23:59 in Moscow
        game = GameProgressService(self.sessions, now=lambda: clock[0])

        self.assertEqual((await game.get_onboarding(self.user_id))["profile"]["energy"], 5)
        self.assertFalse((await game.answer_red_square(self.user_id, "color"))["correct"])
        day_one = await game.answer_red_square(self.user_id, "beautiful")
        self.assertEqual(day_one["profile"], {"xp": 50, "energy": 4, "streak": 1})

        clock[0] = datetime(2026, 9, 1, 21, 1, tzinfo=timezone.utc)  # 00:01 in Moscow
        next_moscow_day = await game.get_onboarding(self.user_id)
        self.assertEqual(next_moscow_day["profile"], {"xp": 50, "energy": 5, "streak": 1})
        self.assertEqual(next_moscow_day["daily"]["completed_quests"], 0)

        self.assertFalse((await game.answer_moscow_quest(
            self.user_id, "moscow-spasskaya-tower", "1547",
        ))["correct"])
        consecutive_day = await game.answer_moscow_quest(
            self.user_id, "moscow-spasskaya-tower", "1491",
        )
        self.assertEqual(consecutive_day["profile"], {"xp": 75, "energy": 4, "streak": 2})
        self.assertEqual(consecutive_day["daily"]["completed_quests"], 1)

        clock[0] = datetime(2026, 9, 4, 9, tzinfo=timezone.utc)  # Moscow day 4: day 3 was skipped
        skipped_day = await game.get_onboarding(self.user_id)
        self.assertEqual(skipped_day["profile"], {"xp": 75, "energy": 5, "streak": 2})
        reset_streak = await game.answer_moscow_quest(self.user_id, "moscow-tsar-bell", "1735")
        self.assertEqual(reset_streak["profile"], {"xp": 100, "energy": 5, "streak": 1})
        self.assertEqual(reset_streak["daily"]["completed_quests"], 1)

    async def test_moscow_daily_rules_use_moscow_date_during_other_timezone_dst(self):
        """The injected clock may be zoned elsewhere; the game day remains Moscow's."""
        los_angeles = ZoneInfo("America/Los_Angeles")
        # US daylight saving time starts earlier that morning. These two local
        # instants still straddle midnight in Moscow (23:59 → 00:01).
        clock = [datetime(2026, 3, 8, 13, 59, tzinfo=los_angeles)]
        game = GameProgressService(self.sessions, now=lambda: clock[0])

        self.assertEqual(game._today().isoformat(), "2026-03-08")
        self.assertFalse((await game.answer_red_square(self.user_id, "color"))["correct"])
        self.assertEqual(
            (await game.answer_red_square(self.user_id, "beautiful"))["daily"]["completed_quests"],
            1,
        )

        clock[0] = datetime(2026, 3, 8, 14, 1, tzinfo=los_angeles)
        refreshed = await game.get_onboarding(self.user_id)
        self.assertEqual(game._today().isoformat(), "2026-03-09")
        self.assertEqual(refreshed["profile"]["energy"], 5)
        self.assertEqual(refreshed["daily"]["completed_quests"], 0)

    async def test_wiki_draft_is_private_until_editorial_publish(self):
        slug = f"moscow-test-{self.user_id[:8]}"
        moscow = await self.wiki.get_published("moscow")
        self.assertEqual(moscow["title"], "Москва")
        self.assertEqual(len(moscow["sources"]), 2)
        self.assertEqual((await self.wiki.get_published_version(moscow["version_id"]))["slug"], "moscow")
        moscow_english = await self.wiki.get_published("moscow", "en")
        self.assertEqual(moscow_english["content_language"], "en")
        self.assertEqual(moscow_english["version_id"], "wiki-moscow-en-v1")
        self.assertEqual(moscow_english["title"], "Moscow")
        japan = await self.wiki.get_published("country-jp")
        self.assertEqual(japan["version_id"], "wiki-country-jp-v1")
        self.assertEqual(japan["title"], "Япония")
        self.assertGreaterEqual(len(japan["sources"]), 3)
        self.assertEqual((await self.wiki.get_published_version(japan["version_id"]))["slug"], "country-jp")
        japan_english = await self.wiki.get_published("country-jp", "en")
        self.assertEqual(japan_english["content_language"], "en")
        self.assertEqual(japan_english["version_id"], "wiki-country-jp-en-v1")
        self.assertEqual([source["url"] for source in japan_english["sources"]], [source["url"] for source in japan["sources"]])
        georgia = await self.wiki.get_published("country-ge")
        self.assertEqual(georgia["version_id"], "wiki-country-ge-v1")
        self.assertEqual(georgia["title"], "Грузия")
        self.assertGreaterEqual(len(georgia["sources"]), 4)
        self.assertEqual((await self.wiki.get_published_version(georgia["version_id"]))["slug"], "country-ge")
        georgia_english = await self.wiki.get_published("country-ge", "en")
        self.assertEqual(georgia_english["content_language"], "en")
        self.assertEqual(georgia_english["version_id"], "wiki-country-ge-en-v1")
        self.assertEqual([source["url"] for source in georgia_english["sources"]], [source["url"] for source in georgia["sources"]])
        russia = await self.wiki.get_published("country-ru")
        self.assertEqual(russia["version_id"], "wiki-country-ru-v1")
        self.assertEqual(russia["title"], "Россия")
        self.assertGreaterEqual(len(russia["sources"]), 4)
        self.assertEqual((await self.wiki.get_published_version(russia["version_id"]))["slug"], "country-ru")
        russia_english = await self.wiki.get_published("country-ru", "en")
        self.assertEqual(russia_english["content_language"], "en")
        self.assertEqual(russia_english["version_id"], "wiki-country-ru-en-v1")
        self.assertEqual([source["url"] for source in russia_english["sources"]], [source["url"] for source in russia["sources"]])
        draft = await self.wiki.create_draft(
            self.user_id,
            slug,
            "Москва: тестовый черновик",
            {"blocks": [{"type": "paragraph", "text": "Проверяемый текст."}]},
            [{"label": "Официальный источник", "url": "https://example.test/source"}],
            "CC BY 4.0",
        )
        self.assertEqual(draft["status"], "draft")
        self.assertEqual([item["id"] for item in await self.wiki.list_authored(self.user_id)], [draft["id"]])
        with self.assertRaises(WikiNotFoundError):
            await self.wiki.get_published(slug)
        review = await self.wiki.submit_for_review(self.user_id, draft["id"])
        self.assertEqual(review["status"], "review")
        self.assertEqual((await self.wiki.list_authored(self.user_id))[0]["status"], "review")
        with self.assertRaises(PermissionError):
            await self.wiki.list_review_queue(self.user_id)
        with self.assertRaises(WikiNotFoundError):
            await self.wiki.get_published(slug)
        async with self.sessions() as db:
            await db.execute(update(User).where(User.id == self.user_id).values(is_editor=True))
            await db.commit()
        self.assertEqual((await self.wiki.list_review_queue(self.user_id))[0]["id"], draft["id"])
        published = await self.wiki.publish_reviewed(self.user_id, draft["id"])
        self.assertEqual(published["title"], "Москва: тестовый черновик")
        self.assertEqual((await self.wiki.get_published(slug))["license"], "CC BY 4.0")
