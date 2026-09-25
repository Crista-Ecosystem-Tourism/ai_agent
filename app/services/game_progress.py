from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import jwt
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.game import (
    GameAttempt,
    GameCity,
    GameContentRevision,
    GameContentTranslation,
    GameDailyProgress,
    GameDistrict,
    GameProfile,
    GameQuest,
    GameQuestCompletion,
    GameRewardLedger,
    GameStamp,
)
from app.db.models.saved_route import SavedRoute
from app.db.models.wiki import WikiArticleVersion
from app.core.social_tokens import shared_quest_reward_key
from app.security.jwt import JWT_ALG, JWT_SECRET


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
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        now: Callable[[], datetime] | None = None,
    ):
        self.session_factory = session_factory
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _today(self) -> date:
        return self._now().astimezone(GAME_TIMEZONE).date()

    async def get_onboarding(self, user_id: str, language: str = "ru") -> dict[str, Any]:
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            content = await self._published_content(db)
            localized_payload, content_language = await self._localized_content(db, content, language)
            stamp = await self._backfill_onboarding_completion(db, user_id)
            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()
            return {
                "content": self._public_content(localized_payload),
                "content_language": content_language,
                "profile": self._profile_payload(profile),
                "daily": daily,
                "completed": stamp is not None,
                "starter_stamp": self._stamp_payload(stamp),
            }

    async def get_passport(self, user_id: str) -> dict[str, Any]:
        """Server-owned game portion of a user's travel passport."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            stamps = list((await db.scalars(
                select(GameStamp)
                .where(GameStamp.user_id == user_id)
                .order_by(GameStamp.earned_at.desc())
            )).all())
            cities = list((await db.scalars(
                select(GameCity).where(GameCity.is_published.is_(True)).order_by(GameCity.tier, GameCity.name)
            )).all())
            completed_rows = (await db.execute(
                select(GameQuest.city_id, GameQuestCompletion.quest_id)
                .join(GameQuestCompletion, GameQuestCompletion.quest_id == GameQuest.id)
                .where(GameQuestCompletion.user_id == user_id)
            )).all()
            completed_by_city: dict[str, int] = {}
            for city_id, _ in completed_rows:
                completed_by_city[city_id] = completed_by_city.get(city_id, 0) + 1
            routes = (await db.execute(
                select(SavedRoute.id, SavedRoute.name, SavedRoute.destination, SavedRoute.updated_at)
                .where(SavedRoute.user_id == user_id)
                .order_by(SavedRoute.updated_at.desc())
            )).all()
            await db.commit()
            return {
                "profile": self._profile_payload(profile),
                "stamps": [self._stamp_payload(stamp) for stamp in stamps],
                "cities": [
                    {"id": city.id, "name": city.name, "completed_quests": completed_by_city.get(city.id, 0), "required_quest_count": city.required_quest_count}
                    for city in cities
                ],
                "routes": [
                    {"id": route.id, "name": route.name, "destination": route.destination, "updated_at": route.updated_at.isoformat() if route.updated_at else None}
                    for route in routes
                ],
            }

    async def create_mini_site_stamp_ticket(self, user_id: str, stamp_keys: list[str]) -> dict[str, Any]:
        """Sign a short-lived, owner-scoped list of earned stamps for explicit sharing."""
        if not isinstance(stamp_keys, list) or not 1 <= len(stamp_keys) <= 20:
            raise ValueError("Select between one and twenty game stamps")
        if any(not isinstance(key, str) or not key.strip() or len(key) > 120 for key in stamp_keys):
            raise ValueError("Invalid game stamp selection")
        if len(stamp_keys) != len(set(stamp_keys)):
            raise ValueError("Game stamp selection contains duplicates")

        async with self.session_factory() as db:
            rows = (await db.execute(
                select(GameStamp, GameContentRevision.payload)
                .join(GameContentRevision, GameContentRevision.id == GameStamp.content_revision_id)
                .where(GameStamp.user_id == user_id, GameStamp.stamp_key.in_(stamp_keys))
            )).all()
        by_key = {stamp.stamp_key: (stamp, payload) for stamp, payload in rows}
        if set(by_key) != set(stamp_keys):
            raise ValueError("One or more selected stamps were not earned by this account")

        safe_stamps = []
        for key in stamp_keys:
            stamp, content = by_key[key]
            fact = content.get("fact") if isinstance(content, dict) else None
            source_url = fact.get("source_url") if isinstance(fact, dict) else None
            source_label = fact.get("source_label") if isinstance(fact, dict) else None
            fact_text = fact.get("text") if isinstance(fact, dict) else None
            if isinstance(source_url, str):
                try:
                    parsed = urlsplit(source_url.strip())
                    source_url = urlunsplit(("https", parsed.netloc, parsed.path, "", "")) \
                        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password else None
                except ValueError:
                    source_url = None
            safe_stamps.append({
                "key": stamp.stamp_key[:120],
                "title": stamp.title.strip()[:200],
                "earned_at": stamp.earned_at.isoformat(),
                "fact": fact_text.strip()[:800] if isinstance(fact_text, str) and fact_text.strip() else None,
                "source_label": source_label.strip()[:160] if isinstance(source_label, str) and source_label.strip() else None,
                "source_url": source_url[:512] if isinstance(source_url, str) else None,
            })

        now = datetime.now(timezone.utc)
        token = jwt.encode({
            "sub": user_id,
            "iss": "crista-ai-agent",
            "aud": "crista-suitcase-mini-site",
            "purpose": "trip-mini-site-stamps",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "stamps": safe_stamps,
        }, JWT_SECRET, algorithm=JWT_ALG)
        return {"ticket": token, "stamps": safe_stamps}

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
            now = self._now()
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

    async def get_city_path(self, user_id: str, city_id: str) -> dict[str, Any]:
        """Return a published city path and server-owned unlock state."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)

            city = await db.scalar(
                select(GameCity).where(GameCity.id == city_id, GameCity.is_published.is_(True))
            )
            if city is None:
                raise GameContentUnavailableError("City path is not published")
            quests = list((await db.scalars(
                select(GameQuest)
                .where(GameQuest.city_id == city.id, GameQuest.is_published.is_(True))
                .order_by(GameQuest.position)
            )).all())
            districts = {
                district.id: district
                for district in (await db.scalars(
                    select(GameDistrict).where(GameDistrict.city_id == city.id)
                )).all()
            }

            completed_ids = set((await db.scalars(
                select(GameQuestCompletion.quest_id).where(GameQuestCompletion.user_id == user_id)
            )).all())
            boss = await self._moscow_boss_summary(db, user_id, city, quests, completed_ids)
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
                    "district": self._district_payload(districts.get(quest.district_id)),
                })
            return {
                "city": {
                    "id": city.id,
                    "name": city.name,
                    "tier": city.tier,
                    "required_quest_count": city.required_quest_count,
                    "completion_stamp": (
                        {"key": city.completion_stamp_key, "title": city.completion_stamp_title}
                        if city.completion_stamp_key and city.completion_stamp_title else None
                    ),
                },
                "profile": self._profile_payload(profile),
                "daily": daily,
                "nodes": nodes,
                "boss": boss,
            }

    async def get_moscow_path(self, user_id: str) -> dict[str, Any]:
        return await self.get_city_path(user_id, "moscow")

    async def get_moscow_boss(self, user_id: str, language: str = "ru") -> dict[str, Any]:
        """Return the city boss only after every published Moscow node is complete."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, content = await self._published_moscow_boss(db)
            await self._ensure_city_boss_unlocked(db, user_id, city)
            localized_payload, content_language = await self._localized_content(db, content, language)
            city_stamp = await self._city_stamp(db, user_id, city)
            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()
            return {
                "city": {"id": city.id, "name": city.name},
                "content": self._public_content(localized_payload),
                "content_language": content_language,
                "profile": self._profile_payload(profile),
                "daily": daily,
                "completed": city_stamp is not None,
                "city_stamp": self._stamp_payload(city_stamp),
                "sandbox_unlocked": city_stamp is not None,
            }

    async def get_moscow_sandbox(self, user_id: str, language: str = "ru") -> dict[str, Any]:
        """Let a city completer freely review published Moscow lessons and sources."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, _ = await self._published_moscow_boss(db)
            city_stamp = await self._city_stamp(db, user_id, city)
            if city_stamp is None:
                raise GameQuestLockedError("Complete the Moscow city boss before using sandbox")
            drill = await self._published_moscow_sandbox_content(db, city)
            localized_drill, content_language = (
                await self._localized_content(db, drill, language) if drill else ({}, "ru")
            )
            quests = list((await db.scalars(
                select(GameQuest)
                .where(GameQuest.city_id == city.id, GameQuest.is_published.is_(True))
                .order_by(GameQuest.position)
            )).all())
            contents = {
                content.id: content
                for content in (await db.scalars(
                    select(GameContentRevision).where(
                        GameContentRevision.id.in_([quest.content_revision_id for quest in quests]),
                        GameContentRevision.is_published.is_(True),
                    )
                )).all()
            }
            wiki_reference = self._public_wiki_reference(drill.payload) if drill else None
            wiki_content_language = "ru" if wiki_reference else None
            if wiki_reference and language == "en":
                english_wiki_version = await db.scalar(
                    select(WikiArticleVersion.id).where(
                        WikiArticleVersion.id == "wiki-moscow-en-v1",
                        WikiArticleVersion.status == "published",
                    )
                )
                if english_wiki_version:
                    wiki_reference = {"slug": "moscow-en", "version_id": english_wiki_version}
                    wiki_content_language = "en"
            lessons = []
            lesson_languages = []
            for quest in quests:
                content = contents.get(quest.content_revision_id)
                if content is None:
                    raise GameContentUnavailableError("Moscow sandbox lesson is not published")
                localized_lesson, lesson_language = await self._localized_content(db, content, language)
                lesson_languages.append(lesson_language)
                public_content = self._public_content(localized_lesson)
                fact = public_content.get("fact", {})
                if not isinstance(fact, dict):
                    raise GameContentUnavailableError("Moscow sandbox lesson fact is invalid")
                lessons.append({
                    "id": quest.id,
                    "position": quest.position,
                    "title": public_content.get("scene", {}).get("title", quest.id),
                    "fact": fact,
                    "question": public_content.get("question", {}),
                    "explanation": self._content_explanation(localized_lesson),
                    "wiki_reference": wiki_reference,
                })
            await db.commit()
            return {
                "city": {"id": city.id, "name": city.name},
                "content_language": content_language,
                "lesson_content_language": "en" if lesson_languages and all(item == "en" for item in lesson_languages) else "ru",
                "activity_content_language": (
                    "en" if language == "en" and all(
                        isinstance(localized_drill.get(section), dict)
                        for section in (
                            "truth_myth", "matching", "timeline", "word_blocks",
                            "price_slider", "photo_scanner",
                        )
                    ) else "ru"
                ),
                "wiki_content_language": wiki_content_language,
                "profile": self._profile_payload(profile),
                "city_stamp": self._stamp_payload(city_stamp),
                "lessons": lessons,
                "drill": self._public_truth_myth_drill(localized_drill) if drill else None,
                "matching": self._public_matching_drill(localized_drill) if drill else None,
                "timeline": self._public_timeline_drill(localized_drill) if drill else None,
                "word_blocks": self._public_word_blocks_drill(localized_drill) if drill else None,
                "price_slider": self._public_price_slider_drill(localized_drill) if drill else None,
                "story": self._public_story_card(localized_drill) if drill else None,
                "photo_scanner": self._public_photo_scanner_drill(localized_drill) if drill else None,
                "wiki_reference": wiki_reference,
                "practice_recovery": self._practice_recovery_payload(profile),
            }

    async def answer_moscow_truth_myth(
        self, user_id: str, statement_id: str, answer_key: str, language: str = "ru",
    ) -> dict[str, Any]:
        """Check an optional sandbox drill without awarding XP or spending energy."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, _ = await self._published_moscow_boss(db)
            if await self._city_stamp(db, user_id, city) is None:
                raise GameQuestLockedError("Complete the Moscow city boss before using sandbox")
            content = await self._published_moscow_sandbox_content(db, city)
            if content is None:
                raise GameContentUnavailableError("Moscow truth-or-myth drill is not published")
            localized_payload, _content_language = await self._localized_content(db, content, language)
            truth_myth = self._truth_myth_payload(content.payload)
            localized_truth_myth = self._truth_myth_payload(localized_payload)
            statements = truth_myth.get("statements")
            if not isinstance(statements, list):
                raise GameContentUnavailableError("Moscow truth-or-myth drill is invalid")
            statement = next(
                (item for item in statements if item.get("id") == statement_id), None,
            )
            localized_statement = next(
                (item for item in localized_truth_myth.get("statements", []) if item.get("id") == statement_id),
                {},
            )
            if not isinstance(statement, dict) or answer_key not in {"truth", "myth"}:
                raise ValueError("Unknown sandbox answer")
            correct_answer = statement.get("correct_answer")
            if correct_answer not in {"truth", "myth"}:
                raise GameContentUnavailableError("Moscow truth-or-myth answer is invalid")
            is_correct = answer_key == correct_answer
            now = self._now()
            db.add(GameAttempt(
                id=uuid.uuid4().hex,
                user_id=user_id,
                content_revision_id=content.id,
                interaction_key=statement_id,
                answer_key=answer_key,
                is_correct=is_correct,
                created_at=now,
            ))
            await db.commit()
            return {
                "correct": is_correct,
                "explanation": localized_statement.get("explanation", statement.get("explanation", "Проверьте источник утверждения.")),
                "profile": self._profile_payload(profile),
            }

    async def answer_moscow_matching(
        self, user_id: str, answers: list[dict[str, str]], language: str = "ru",
    ) -> dict[str, Any]:
        """Check sandbox matching on the server without changing energy or XP."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, _ = await self._published_moscow_boss(db)
            if await self._city_stamp(db, user_id, city) is None:
                raise GameQuestLockedError("Complete the Moscow city boss before using sandbox")
            content = await self._published_moscow_sandbox_content(db, city)
            if content is None:
                raise GameContentUnavailableError("Moscow matching drill is not published")
            localized_payload, _content_language = await self._localized_content(db, content, language)
            matching = self._matching_payload(content.payload)
            localized_matching = self._matching_payload(localized_payload)
            pairs = matching.get("pairs") if matching else None
            choices = matching.get("choices") if matching else None
            if not isinstance(pairs, list) or not isinstance(choices, list) or len(pairs) != 3:
                raise GameContentUnavailableError("Moscow matching drill is invalid")

            submitted = {answer.get("pair_id"): answer.get("choice_id") for answer in answers}
            pair_ids = {pair.get("id") for pair in pairs if isinstance(pair, dict)}
            choice_ids = {choice.get("id") for choice in choices if isinstance(choice, dict)}
            if (
                len(submitted) != 3
                or None in submitted
                or set(submitted) != pair_ids
                or len(set(submitted.values())) != 3
                or not set(submitted.values()).issubset(choice_ids)
            ):
                raise ValueError("All matching pairs must be answered exactly once")

            now = self._now()
            feedback = []
            incorrect_pairs = []
            localized_pairs = {
                pair.get("id"): pair
                for pair in (localized_matching or {}).get("pairs", [])
                if isinstance(pair, dict)
            }
            for pair in pairs:
                if not isinstance(pair, dict):
                    raise GameContentUnavailableError("Moscow matching pair is invalid")
                pair_id = pair.get("id")
                correct_choice_id = pair.get("correct_choice_id")
                if not isinstance(pair_id, str) or not isinstance(correct_choice_id, str):
                    raise GameContentUnavailableError("Moscow matching answer is invalid")
                is_correct = submitted[pair_id] == correct_choice_id
                if not is_correct:
                    incorrect_pairs.append(pair_id)
                feedback.append({
                    "pair_id": pair_id,
                    "correct": is_correct,
                    "explanation": localized_pairs.get(pair_id, {}).get("explanation", pair.get("explanation", "Проверьте связь места и даты.")),
                })
                db.add(GameAttempt(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    content_revision_id=content.id,
                    interaction_key=pair_id,
                    answer_key=submitted[pair_id],
                    is_correct=is_correct,
                    created_at=now,
                ))
            await db.commit()
            return {
                "correct": not incorrect_pairs,
                "incorrect_pairs": incorrect_pairs,
                "feedback": feedback,
                "profile": self._profile_payload(profile),
            }

    async def answer_moscow_timeline(
        self, user_id: str, ordered_ids: list[str], language: str = "ru",
    ) -> dict[str, Any]:
        """Check a sandbox chronology without spending energy or awarding XP."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, _ = await self._published_moscow_boss(db)
            if await self._city_stamp(db, user_id, city) is None:
                raise GameQuestLockedError("Complete the Moscow city boss before using sandbox")
            content = await self._published_moscow_sandbox_content(db, city)
            if content is None:
                raise GameContentUnavailableError("Moscow timeline drill is not published")
            localized_payload, _content_language = await self._localized_content(db, content, language)
            timeline = self._timeline_payload(content.payload)
            localized_timeline = self._timeline_payload(localized_payload)
            items = timeline.get("items") if timeline else None
            if not isinstance(items, list) or len(items) != 3:
                raise GameContentUnavailableError("Moscow timeline drill is invalid")
            item_ids = [item.get("id") for item in items if isinstance(item, dict)]
            if len(item_ids) != 3 or len(set(ordered_ids)) != 3 or set(ordered_ids) != set(item_ids):
                raise ValueError("All timeline events must be ordered exactly once")
            ordered_items = sorted(
                items,
                key=lambda item: item.get("correct_position") if isinstance(item, dict) else -1,
            )
            expected_ids = [item.get("id") for item in ordered_items]
            if any(not isinstance(item_id, str) for item_id in expected_ids):
                raise GameContentUnavailableError("Moscow timeline answer is invalid")
            is_correct = ordered_ids == expected_ids
            now = self._now()
            item_by_id = {item.get("id"): item for item in items if isinstance(item, dict)}
            localized_items = {
                item.get("id"): item
                for item in (localized_timeline or {}).get("items", [])
                if isinstance(item, dict)
            }
            feedback = []
            for position, item_id in enumerate(ordered_ids, start=1):
                item = item_by_id[item_id]
                correct_position = item.get("correct_position")
                item_correct = correct_position == position
                feedback.append({
                    "item_id": item_id,
                    "correct": item_correct,
                    "explanation": localized_items.get(item_id, {}).get("explanation", item.get("explanation", "Проверьте дату события.")),
                })
                db.add(GameAttempt(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    content_revision_id=content.id,
                    interaction_key=item_id,
                    answer_key=str(position),
                    is_correct=item_correct,
                    created_at=now,
                ))
            await db.commit()
            return {
                "correct": is_correct,
                "expected_order": expected_ids if is_correct else None,
                "feedback": feedback,
                "profile": self._profile_payload(profile),
            }

    async def answer_moscow_word_blocks(
        self, user_id: str, ordered_ids: list[str], language: str = "ru",
    ) -> dict[str, Any]:
        """Check a sandbox word-order exercise without spending energy or XP."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, _ = await self._published_moscow_boss(db)
            if await self._city_stamp(db, user_id, city) is None:
                raise GameQuestLockedError("Complete the Moscow city boss before using sandbox")
            content = await self._published_moscow_sandbox_content(db, city)
            if content is None:
                raise GameContentUnavailableError("Moscow word-blocks drill is not published")
            localized_payload, _content_language = await self._localized_content(db, content, language)
            word_blocks = self._word_blocks_payload(content.payload)
            localized_word_blocks = self._word_blocks_payload(localized_payload)
            blocks = word_blocks.get("blocks") if word_blocks else None
            expected_order = word_blocks.get("expected_order") if word_blocks else None
            if not isinstance(blocks, list) or not isinstance(expected_order, list) or len(blocks) != 4:
                raise GameContentUnavailableError("Moscow word-blocks drill is invalid")
            block_ids = [block.get("id") for block in blocks if isinstance(block, dict)]
            if len(block_ids) != 4 or len(set(expected_order)) != 4 or set(expected_order) != set(block_ids):
                raise GameContentUnavailableError("Moscow word-blocks answer is invalid")
            if len(set(ordered_ids)) != 4 or set(ordered_ids) != set(block_ids):
                raise ValueError("All word blocks must be ordered exactly once")
            is_correct = ordered_ids == expected_order
            now = self._now()
            for position, block_id in enumerate(ordered_ids, start=1):
                db.add(GameAttempt(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    content_revision_id=content.id,
                    interaction_key=block_id,
                    answer_key=str(position),
                    is_correct=block_id == expected_order[position - 1],
                    created_at=now,
                ))
            await db.commit()
            return {
                "correct": is_correct,
                "explanation": (localized_word_blocks or {}).get("explanation", word_blocks.get("explanation", "Проверьте порядок слов и повторите попытку.")),
                "profile": self._profile_payload(profile),
            }

    async def answer_moscow_price_slider(self, user_id: str, value: int, language: str = "ru") -> dict[str, Any]:
        """Check a historic-price estimate without changing sandbox rewards or energy."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, _ = await self._published_moscow_boss(db)
            if await self._city_stamp(db, user_id, city) is None:
                raise GameQuestLockedError("Complete the Moscow city boss before using sandbox")
            content = await self._published_moscow_sandbox_content(db, city)
            if content is None:
                raise GameContentUnavailableError("Moscow price-slider drill is not published")
            localized_payload, _content_language = await self._localized_content(db, content, language)
            price_slider = self._price_slider_payload(content.payload)
            localized_price_slider = self._price_slider_payload(localized_payload)
            if price_slider is None:
                raise GameContentUnavailableError("Moscow price-slider drill is invalid")
            minimum = price_slider.get("min")
            maximum = price_slider.get("max")
            target = price_slider.get("target")
            tolerance = price_slider.get("tolerance")
            if not all(isinstance(item, int) for item in (minimum, maximum, target, tolerance)):
                raise GameContentUnavailableError("Moscow price-slider answer is invalid")
            if minimum > maximum or target < minimum or target > maximum or tolerance < 0:
                raise GameContentUnavailableError("Moscow price-slider answer is invalid")
            if value < minimum or value > maximum:
                raise ValueError("Price estimate is outside the configured range")
            is_correct = abs(value - target) <= tolerance
            now = self._now()
            db.add(GameAttempt(
                id=uuid.uuid4().hex,
                user_id=user_id,
                content_revision_id=content.id,
                interaction_key="price-slider",
                answer_key=str(value),
                is_correct=is_correct,
                created_at=now,
            ))
            await db.commit()
            return {
                "correct": is_correct,
                "explanation": (localized_price_slider or {}).get("explanation", price_slider.get("explanation", "Проверьте цену в источнике упражнения.")),
                "profile": self._profile_payload(profile),
            }

    async def answer_moscow_photo_scanner(self, user_id: str, hotspot_id: str, language: str = "ru") -> dict[str, Any]:
        """Check a photograph hotspot on the server without changing sandbox rewards or energy."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, _ = await self._published_moscow_boss(db)
            if await self._city_stamp(db, user_id, city) is None:
                raise GameQuestLockedError("Complete the Moscow city boss before using sandbox")
            content = await self._published_moscow_sandbox_content(db, city)
            if content is None:
                raise GameContentUnavailableError("Moscow photo-scanner drill is not published")
            localized_payload, _content_language = await self._localized_content(db, content, language)
            scanner = self._photo_scanner_payload(content.payload)
            localized_scanner = self._photo_scanner_payload(localized_payload)
            hotspots = scanner.get("hotspots") if scanner else None
            correct_hotspot_id = scanner.get("correct_hotspot_id") if scanner else None
            hotspot_ids = {item.get("id") for item in hotspots if isinstance(item, dict)} if isinstance(hotspots, list) else set()
            if not hotspot_ids or not isinstance(correct_hotspot_id, str) or correct_hotspot_id not in hotspot_ids:
                raise GameContentUnavailableError("Moscow photo-scanner drill is invalid")
            if hotspot_id not in hotspot_ids:
                raise ValueError("Unknown scanner hotspot")
            is_correct = hotspot_id == correct_hotspot_id
            db.add(GameAttempt(
                id=uuid.uuid4().hex,
                user_id=user_id,
                content_revision_id=content.id,
                interaction_key="photo-scanner",
                answer_key=hotspot_id,
                is_correct=is_correct,
                created_at=self._now(),
            ))
            await db.commit()
            return {
                "correct": is_correct,
                "explanation": (localized_scanner or {}).get("explanation", scanner.get("explanation", "Сверь деталь со снимком и источником.")),
                "profile": self._profile_payload(profile),
            }

    async def restore_moscow_energy_from_practice(self, user_id: str) -> dict[str, Any]:
        """Award one daily energy point only after a genuine correct sandbox repeat."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, _ = await self._published_moscow_boss(db)
            if await self._city_stamp(db, user_id, city) is None:
                raise GameQuestLockedError("Complete the Moscow city boss before using sandbox")
            content = await self._published_moscow_sandbox_content(db, city)
            if content is None:
                raise GameContentUnavailableError("Moscow sandbox is not published")
            today = self._today()
            if profile.energy >= DAILY_ENERGY:
                raise ValueError("Энергия уже полностью восстановлена")
            if profile.practice_recovered_on == today:
                raise ValueError("Сегодня энергия за повторение уже восстановлена")
            practiced = await db.scalar(
                select(GameAttempt.id).where(
                    GameAttempt.user_id == user_id,
                    GameAttempt.content_revision_id == content.id,
                    GameAttempt.is_correct.is_(True),
                    GameAttempt.created_at >= datetime.combine(today, datetime.min.time(), tzinfo=GAME_TIMEZONE),
                ).limit(1)
            )
            if practiced is None:
                raise ValueError("Сначала правильно заверши любое упражнение в песочнице")
            new_energy = await db.scalar(
                update(GameProfile)
                .where(
                    GameProfile.user_id == user_id,
                    GameProfile.energy < DAILY_ENERGY,
                    GameProfile.practice_recovered_on.is_distinct_from(today),
                )
                .values(
                    energy=GameProfile.energy + 1,
                    practice_recovered_on=today,
                    updated_at=self._now(),
                )
                .returning(GameProfile.energy)
            )
            if new_energy is None:
                raise ValueError("Сегодня энергия за повторение уже восстановлена")
            profile.energy = new_energy
            profile.practice_recovered_on = today
            await db.commit()
            return {
                "profile": self._profile_payload(profile),
                "practice_recovery": self._practice_recovery_payload(profile),
            }

    async def answer_moscow_boss(
        self, user_id: str, answers: list[dict[str, str]], language: str = "ru",
    ) -> dict[str, Any]:
        """Check all three boss answers on the server and award the city stamp once."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            city, content = await self._published_moscow_boss(db)
            await self._ensure_city_boss_unlocked(db, user_id, city)
            localized_payload, _content_language = await self._localized_content(db, content, language)

            questions = content.payload.get("questions")
            if not isinstance(questions, list) or len(questions) != 3:
                raise GameContentUnavailableError("City boss must contain exactly three questions")
            answer_by_question = {answer.get("question_id"): answer.get("answer_key") for answer in answers}
            question_ids = {question.get("id") for question in questions}
            if (
                len(answer_by_question) != 3
                or None in answer_by_question
                or set(answer_by_question) != question_ids
            ):
                raise ValueError("All boss questions must be answered exactly once")

            now = self._now()
            incorrect_answers = 0
            feedback = []
            localized_questions = {
                question.get("id"): question
                for question in localized_payload.get("questions", [])
                if isinstance(question, dict)
            }
            for question in questions:
                question_id = question.get("id")
                options = question.get("options", [])
                allowed_answers = {option.get("id") for option in options}
                answer_key = answer_by_question[question_id]
                if answer_key not in allowed_answers:
                    raise ValueError("Unknown answer option")
                is_correct = answer_key == question.get("correct_option_id")
                if not is_correct:
                    incorrect_answers += 1
                feedback.append({
                    "question_id": question_id,
                    "correct": is_correct,
                    "explanation": localized_questions.get(question_id, {}).get(
                        "explanation", question.get("explanation", "Ответ подтверждается источником урока.")
                    ),
                })
                db.add(GameAttempt(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    content_revision_id=content.id,
                    interaction_key=str(question_id),
                    answer_key=answer_key,
                    is_correct=is_correct,
                    created_at=now,
                ))

            city_stamp: GameStamp | None = None
            if incorrect_answers:
                profile.energy = max(0, profile.energy - incorrect_answers)
                profile.updated_at = now
            else:
                if not city.completion_stamp_key or not city.completion_stamp_title:
                    raise GameContentUnavailableError("City completion stamp is not configured")
                await db.execute(
                    pg_insert(GameStamp)
                    .values(
                        id=uuid.uuid4().hex,
                        user_id=user_id,
                        stamp_key=city.completion_stamp_key,
                        content_revision_id=content.id,
                        title=city.completion_stamp_title,
                        earned_at=now,
                    )
                    .on_conflict_do_nothing(constraint="uq_game_stamp_user_key")
                )
                city_stamp = await self._city_stamp(db, user_id, city)

            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()
            return {
                "correct": incorrect_answers == 0,
                "incorrect_answers": incorrect_answers,
                "profile": self._profile_payload(profile),
                "daily": daily,
                "completed": city_stamp is not None,
                "city_stamp": self._stamp_payload(city_stamp),
                "sandbox_unlocked": city_stamp is not None,
                "feedback": feedback,
            }

    async def get_city_quest(self, user_id: str, city_id: str, quest_id: str, language: str = "ru") -> dict[str, Any]:
        """Return a published city lesson only when its server prerequisite is met."""
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            quest, content = await self._published_city_quest(db, city_id, quest_id)
            await self._ensure_quest_unlocked(db, user_id, quest)
            localized_payload, content_language = await self._localized_content(db, content, language)
            completed = await db.get(GameQuestCompletion, (user_id, quest.id))
            stamp = await self._quest_stamp(db, user_id, content)
            daily = await self._daily_payload(db, user_id, profile)
            await db.commit()
            return {
                "quest": self._quest_payload(quest),
                "content": self._public_content(localized_payload),
                "content_language": content_language,
                "profile": self._profile_payload(profile),
                "daily": daily,
                "completed": completed is not None,
                "stamp": self._stamp_payload(stamp),
            }

    async def get_moscow_quest(self, user_id: str, quest_id: str, language: str = "ru") -> dict[str, Any]:
        return await self.get_city_quest(user_id, "moscow", quest_id, language)

    async def answer_city_quest(
        self, user_id: str, city_id: str, quest_id: str, answer_key: str, language: str = "ru",
    ) -> dict[str, Any]:
        async with self.session_factory() as db:
            profile = await self._ensure_profile(db, user_id)
            await self._backfill_onboarding_completion(db, user_id)
            quest, content = await self._published_city_quest(db, city_id, quest_id)
            await self._ensure_quest_unlocked(db, user_id, quest)
            localized_payload, _content_language = await self._localized_content(db, content, language)

            question = content.payload.get("question", {})
            options = question.get("options", [])
            allowed_answers = {option.get("id") for option in options}
            if answer_key not in allowed_answers:
                raise ValueError("Unknown answer option")

            is_correct = answer_key == question.get("correct_option_id")
            now = self._now()
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
            explanation = self._content_explanation(localized_payload)
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
                "explanation": explanation,
            }

    async def answer_moscow_quest(
        self, user_id: str, quest_id: str, answer_key: str, language: str = "ru",
    ) -> dict[str, Any]:
        return await self.answer_city_quest(user_id, "moscow", quest_id, answer_key, language)

    async def _ensure_profile(self, db: AsyncSession, user_id: str) -> GameProfile:
        today = self._today()
        profile = await db.get(GameProfile, user_id)
        if profile is None:
            # On the first page load the onboarding and path requests may run
            # concurrently.  Let PostgreSQL elect the creator so the second
            # request reads the same profile instead of failing on the PK.
            await db.execute(
                pg_insert(GameProfile)
                .values(
                    user_id=user_id,
                    xp=0,
                    energy=DAILY_ENERGY,
                    energy_refreshed_on=today,
                    streak=0,
                )
                .on_conflict_do_nothing(index_elements=["user_id"])
            )
            profile = await db.get(GameProfile, user_id)
            if profile is None:
                raise RuntimeError("Game profile could not be created")
        elif profile.energy_refreshed_on < today:
            profile.energy = DAILY_ENERGY
            profile.energy_refreshed_on = today
            profile.updated_at = self._now()
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

    async def award_shared_quest_bonus(
        self,
        db: AsyncSession,
        user_id: str,
        quest_id: str,
        xp: int,
        awarded_at: datetime,
    ) -> int:
        """Credit one stable team-quest bonus through the existing reward ledger.

        The team-quest caller must keep this in the same transaction as completion.
        Replays return zero because GameRewardLedger uniquely keys user + reward_key.
        """
        if xp <= 0:
            return 0
        await self._ensure_profile(db, user_id)
        credited = await self._record_reward(
            db,
            user_id,
            quest_id,
            shared_quest_reward_key(quest_id),
            xp,
            awarded_at,
        )
        if credited:
            await db.execute(
                update(GameProfile)
                .where(GameProfile.user_id == user_id)
                .values(xp=GameProfile.xp + credited, updated_at=awarded_at)
            )
        return credited

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

    async def _daily_payload(
        self, db: AsyncSession, user_id: str, profile: GameProfile,
    ) -> dict[str, Any]:
        today = self._today()
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

    async def _published_city_quest(
        self, db: AsyncSession, city_id: str, quest_id: str,
    ) -> tuple[GameQuest, GameContentRevision]:
        quest = await db.scalar(
            select(GameQuest)
            .join(GameCity, GameQuest.city_id == GameCity.id)
            .where(
                GameQuest.id == quest_id,
                GameQuest.is_published.is_(True),
                GameCity.id == city_id,
                GameCity.is_published.is_(True),
            )
        )
        if quest is None:
            raise GameContentUnavailableError("City quest is not published")
        content = await db.scalar(
            select(GameContentRevision).where(
                GameContentRevision.id == quest.content_revision_id,
                GameContentRevision.is_published.is_(True),
            )
        )
        if content is None:
            raise GameContentUnavailableError("City quest content is not published")
        return quest, content

    @staticmethod
    async def _localized_content(db: AsyncSession, content: GameContentRevision, language: str) -> tuple[dict[str, Any], str]:
        """Overlay a published translation for display while canonical answer IDs remain authoritative."""
        if language == "ru":
            return content.payload, "ru"
        if language != "en":
            return content.payload, "ru"
        translation = await db.scalar(
            select(GameContentTranslation).where(
                GameContentTranslation.content_revision_id == content.id,
                GameContentTranslation.language == language,
                GameContentTranslation.is_published.is_(True),
            )
        )
        if translation is None:
            return content.payload, "ru"
        localized = dict(content.payload)
        for section in (
            "scene", "chris", "fact", "question", "questions", "sources", "reward", "story",
            "truth_myth", "matching", "timeline", "word_blocks", "price_slider", "photo_scanner",
        ):
            translated_section = translation.payload.get(section)
            if isinstance(translated_section, dict):
                localized[section] = {**content.payload.get(section, {}), **translated_section}
        return localized, language

    async def _published_moscow_boss(
        self, db: AsyncSession,
    ) -> tuple[GameCity, GameContentRevision]:
        city = await db.scalar(
            select(GameCity).where(GameCity.id == "moscow", GameCity.is_published.is_(True))
        )
        if city is None or not city.boss_content_revision_id:
            raise GameContentUnavailableError("Moscow city boss is not published")
        content = await db.scalar(
            select(GameContentRevision).where(
                GameContentRevision.id == city.boss_content_revision_id,
                GameContentRevision.is_published.is_(True),
            )
        )
        if content is None:
            raise GameContentUnavailableError("Moscow city boss content is not published")
        return city, content

    @staticmethod
    async def _published_moscow_sandbox_content(
        db: AsyncSession, city: GameCity,
    ) -> GameContentRevision | None:
        if not city.sandbox_content_revision_id:
            return None
        return await db.scalar(
            select(GameContentRevision).where(
                GameContentRevision.id == city.sandbox_content_revision_id,
                GameContentRevision.is_published.is_(True),
            )
        )

    async def _moscow_boss_summary(
        self,
        db: AsyncSession,
        user_id: str,
        city: GameCity,
        quests: list[GameQuest],
        completed_ids: set[str],
    ) -> dict[str, Any] | None:
        if not city.boss_content_revision_id:
            return None
        content = await db.scalar(
            select(GameContentRevision).where(
                GameContentRevision.id == city.boss_content_revision_id,
                GameContentRevision.is_published.is_(True),
            )
        )
        if content is None:
            return None
        questions = content.payload.get("questions")
        if not isinstance(questions, list) or len(questions) != 3:
            return None
        quest_ids = {quest.id for quest in quests}
        unlocked = (
            len(quest_ids) >= city.required_quest_count
            and completed_ids.issuperset(quest_ids)
        )
        city_stamp = await self._city_stamp(db, user_id, city)
        scene = content.payload.get("scene", {})
        return {
            "title": scene.get("title", "Финальный круг Москвы"),
            "question_count": len(questions),
            "unlocked": unlocked,
            "completed": city_stamp is not None,
            "sandbox_unlocked": city_stamp is not None,
        }

    @staticmethod
    async def _ensure_city_boss_unlocked(
        db: AsyncSession, user_id: str, city: GameCity,
    ) -> None:
        quest_ids = set((await db.scalars(
            select(GameQuest.id).where(
                GameQuest.city_id == city.id,
                GameQuest.is_published.is_(True),
            )
        )).all())
        if len(quest_ids) < city.required_quest_count:
            raise GameContentUnavailableError("Moscow path is incomplete")
        completed_ids = set((await db.scalars(
            select(GameQuestCompletion.quest_id).where(
                GameQuestCompletion.user_id == user_id,
                GameQuestCompletion.quest_id.in_(quest_ids),
            )
        )).all())
        if completed_ids != quest_ids:
            raise GameQuestLockedError("Complete every Moscow quest before the city boss")

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
        public_payload = dict(payload)
        question = dict(payload.get("question", {}))
        question.pop("correct_option_id", None)
        public_payload["question"] = question
        if isinstance(payload.get("questions"), list):
            public_payload["questions"] = [
                {**question, "correct_option_id": None}
                for question in payload["questions"]
            ]
            for question in public_payload["questions"]:
                question.pop("correct_option_id", None)
        return public_payload

    @staticmethod
    def _content_explanation(payload: dict[str, Any]) -> str:
        explanation = payload.get("explanation")
        if isinstance(explanation, str) and explanation.strip():
            return explanation
        fact = payload.get("fact", {})
        if isinstance(fact, dict) and isinstance(fact.get("text"), str):
            return fact["text"]
        return "Объяснение доступно в источнике урока."

    @staticmethod
    def _public_truth_myth_drill(payload: dict[str, Any]) -> dict[str, Any]:
        drill = GameProgressService._truth_myth_payload(payload)
        statements = drill.get("statements")
        if not isinstance(statements, list):
            raise GameContentUnavailableError("Moscow truth-or-myth drill is invalid")
        return {
            "title": drill.get("title", "Правда или миф"),
            "intro": drill.get("intro", "Выбери ответ и проверь объяснение."),
            "statements": [
                {"id": statement.get("id"), "text": statement.get("text")}
                for statement in statements
                if isinstance(statement, dict)
            ],
        }

    @staticmethod
    def _truth_myth_payload(payload: dict[str, Any]) -> dict[str, Any]:
        nested = payload.get("truth_myth")
        return nested if isinstance(nested, dict) else payload

    @staticmethod
    def _matching_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
        matching = payload.get("matching")
        return matching if isinstance(matching, dict) else None

    @staticmethod
    def _public_matching_drill(payload: dict[str, Any]) -> dict[str, Any] | None:
        matching = GameProgressService._matching_payload(payload)
        if matching is None:
            return None
        pairs = matching.get("pairs")
        choices = matching.get("choices")
        if not isinstance(pairs, list) or not isinstance(choices, list):
            raise GameContentUnavailableError("Moscow matching drill is invalid")
        return {
            "title": matching.get("title", "Соедини эпохи"),
            "intro": matching.get("intro", "Сопоставь место и год, затем проверь ответ."),
            "pairs": [
                {"id": pair.get("id"), "left": pair.get("left")}
                for pair in pairs
                if isinstance(pair, dict)
            ],
            "choices": [
                {"id": choice.get("id"), "label": choice.get("label")}
                for choice in choices
                if isinstance(choice, dict)
            ],
        }

    @staticmethod
    def _timeline_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
        timeline = payload.get("timeline")
        return timeline if isinstance(timeline, dict) else None

    @staticmethod
    def _public_timeline_drill(payload: dict[str, Any]) -> dict[str, Any] | None:
        timeline = GameProgressService._timeline_payload(payload)
        if timeline is None:
            return None
        items = timeline.get("items")
        if not isinstance(items, list):
            raise GameContentUnavailableError("Moscow timeline drill is invalid")
        return {
            "title": timeline.get("title", "Собери хронологию"),
            "intro": timeline.get("intro", "Расставь события от раннего к позднему."),
            "items": [
                {"id": item.get("id"), "label": item.get("label")}
                for item in items
                if isinstance(item, dict)
            ],
        }

    @staticmethod
    def _word_blocks_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
        word_blocks = payload.get("word_blocks")
        return word_blocks if isinstance(word_blocks, dict) else None

    @staticmethod
    def _public_word_blocks_drill(payload: dict[str, Any]) -> dict[str, Any] | None:
        word_blocks = GameProgressService._word_blocks_payload(payload)
        if word_blocks is None:
            return None
        blocks = word_blocks.get("blocks")
        if not isinstance(blocks, list):
            raise GameContentUnavailableError("Moscow word-blocks drill is invalid")
        return {
            "title": word_blocks.get("title", "Собери фразу"),
            "intro": word_blocks.get("intro", "Расставь слова в правильном порядке."),
            "blocks": [
                {"id": block.get("id"), "label": block.get("label")}
                for block in blocks
                if isinstance(block, dict)
            ],
        }

    @staticmethod
    def _price_slider_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
        price_slider = payload.get("price_slider")
        return price_slider if isinstance(price_slider, dict) else None

    @staticmethod
    def _public_price_slider_drill(payload: dict[str, Any]) -> dict[str, Any] | None:
        price_slider = GameProgressService._price_slider_payload(payload)
        if price_slider is None:
            return None
        minimum = price_slider.get("min")
        maximum = price_slider.get("max")
        step = price_slider.get("step")
        if not all(isinstance(item, int) for item in (minimum, maximum, step)) or minimum >= maximum or step <= 0:
            raise GameContentUnavailableError("Moscow price-slider drill is invalid")
        return {
            "title": price_slider.get("title", "Угадай цену"),
            "intro": price_slider.get("intro", "Выбери оценку и проверь ответ."),
            "question": price_slider.get("question", "Какой была цена?"),
            "fact_date": price_slider.get("fact_date"),
            "unit": price_slider.get("unit", "₽"),
            "min": minimum,
            "max": maximum,
            "step": step,
        }

    @staticmethod
    def _public_story_card(payload: dict[str, Any]) -> dict[str, Any] | None:
        story = payload.get("story")
        if not isinstance(story, dict):
            return None
        required = ("title", "image_url", "image_alt", "fact", "source_url")
        if not all(isinstance(story.get(key), str) and story[key].strip() for key in required):
            raise GameContentUnavailableError("Moscow Story card is invalid")
        return {
            "title": story["title"],
            "eyebrow": story.get("eyebrow", "Story"),
            "image_url": story["image_url"],
            "image_alt": story["image_alt"],
            "media_credit": story.get("media_credit", "Иллюстрация Crista"),
            "fact": story["fact"],
            "source_label": story.get("source_label", "Открыть источник"),
            "source_url": story["source_url"],
            "note": story.get("note", "Проверьте факт по первоисточнику."),
        }

    @staticmethod
    def _photo_scanner_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
        scanner = payload.get("photo_scanner")
        return scanner if isinstance(scanner, dict) else None

    @staticmethod
    def _public_photo_scanner_drill(payload: dict[str, Any]) -> dict[str, Any] | None:
        scanner = GameProgressService._photo_scanner_payload(payload)
        if scanner is None:
            return None
        required = ("title", "image_url", "image_alt", "question", "media_credit", "media_source_url", "license")
        if not all(isinstance(scanner.get(key), str) and scanner[key].strip() for key in required):
            raise GameContentUnavailableError("Moscow photo-scanner drill is invalid")
        hotspots = scanner.get("hotspots")
        if not isinstance(hotspots, list) or len(hotspots) < 2:
            raise GameContentUnavailableError("Moscow photo-scanner hotspots are invalid")
        public_hotspots = []
        for hotspot in hotspots:
            if not isinstance(hotspot, dict) or not isinstance(hotspot.get("id"), str):
                raise GameContentUnavailableError("Moscow photo-scanner hotspot is invalid")
            coordinates = [hotspot.get(key) for key in ("x", "y", "width", "height")]
            if not all(isinstance(value, int) and 0 <= value <= 100 for value in coordinates):
                raise GameContentUnavailableError("Moscow photo-scanner hotspot is invalid")
            public_hotspots.append({"id": hotspot["id"], "x": hotspot["x"], "y": hotspot["y"], "width": hotspot["width"], "height": hotspot["height"]})
        return {
            "title": scanner["title"],
            "intro": scanner.get("intro", "Отметь область на фотографии и получи объяснение."),
            "question": scanner["question"],
            "image_url": scanner["image_url"],
            "image_alt": scanner["image_alt"],
            "media_credit": scanner["media_credit"],
            "media_source_url": scanner["media_source_url"],
            "license": scanner["license"],
            "field_note": scanner.get("field_note", "Это экранное упражнение, а не AR-навигация."),
            "hotspots": public_hotspots,
        }

    @staticmethod
    def _public_wiki_reference(payload: dict[str, Any]) -> dict[str, str] | None:
        reference = payload.get("wiki_reference")
        if not isinstance(reference, dict):
            return None
        slug, version_id = reference.get("slug"), reference.get("version_id")
        if not isinstance(slug, str) or not isinstance(version_id, str) or not slug or not version_id:
            raise GameContentUnavailableError("Moscow sandbox Wiki reference is invalid")
        return {"slug": slug, "version_id": version_id}

    @staticmethod
    def _profile_payload(profile: GameProfile) -> dict[str, Any]:
        return {"xp": profile.xp, "energy": profile.energy, "streak": profile.streak}

    def _practice_recovery_payload(self, profile: GameProfile) -> dict[str, Any]:
        today = self._today()
        return {
            "available": profile.energy < DAILY_ENERGY and profile.practice_recovered_on != today,
            "used_today": profile.practice_recovered_on == today,
            "amount": 1,
        }

    @staticmethod
    def _quest_payload(quest: GameQuest) -> dict[str, Any]:
        return {
            "id": quest.id,
            "kind": quest.kind,
            "position": quest.position,
            "prerequisite_quest_id": quest.prerequisite_quest_id,
        }

    @staticmethod
    def _district_payload(district: GameDistrict | None) -> dict[str, Any] | None:
        if district is None:
            return None
        return {"id": district.id, "name": district.name, "position": district.position}

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
    async def _city_stamp(
        db: AsyncSession, user_id: str, city: GameCity,
    ) -> GameStamp | None:
        if not city.completion_stamp_key:
            return None
        return await db.scalar(
            select(GameStamp).where(
                GameStamp.user_id == user_id,
                GameStamp.stamp_key == city.completion_stamp_key,
            )
        )

    @staticmethod
    def _stamp_payload(stamp: GameStamp | None) -> dict[str, Any] | None:
        if stamp is None:
            return None
        return {"key": stamp.stamp_key, "title": stamp.title, "earned_at": stamp.earned_at}
