import uuid
import unittest
from datetime import datetime, timezone

import jwt
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.dsn import get_database_url
from app.db.models.auth import User
from app.db.models.game import GameContentRevision, GameStamp
from app.security.jwt import JWT_ALG, JWT_SECRET
from app.services.game_progress import GameProgressService


class GameStampShareIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Exercises owner-bound share tickets against an already-migrated disposable DB."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(get_database_url())
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.user_id = uuid.uuid4().hex
        self.other_user_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add_all([
                User(id=self.user_id, email=f"stamp-{self.user_id}@example.test", name="Owner", is_active=True,
                     auth_provider="test", created_at=now, updated_at=now),
                User(id=self.other_user_id, email=f"stamp-{self.other_user_id}@example.test", name="Other", is_active=True,
                     auth_provider="test", created_at=now, updated_at=now),
            ])
            db.add(GameContentRevision(
                id=f"share-{self.user_id}", kind="fact-quiz", is_published=True,
                published_at=now, payload={"fact": {
                    "text": "The verified fact.", "source_label": "Official source",
                    "source_url": "https://example.test/fact?tracking=remove#section",
                }},
                created_at=now, updated_at=now,
            ))
            db.add(GameStamp(
                id=uuid.uuid4().hex, user_id=self.user_id, stamp_key="earned-stamp",
                content_revision_id=f"share-{self.user_id}", title="Earned stamp", earned_at=now,
            ))
            await db.commit()
        self.service = GameProgressService(self.sessions)

    async def asyncTearDown(self):
        async with self.sessions() as db:
            await db.execute(GameStamp.__table__.delete().where(
                GameStamp.user_id.in_([self.user_id, self.other_user_id])
            ))
            await db.execute(GameContentRevision.__table__.delete().where(
                GameContentRevision.id == f"share-{self.user_id}"
            ))
            await db.execute(User.__table__.delete().where(
                User.id.in_([self.user_id, self.other_user_id])
            ))
            await db.commit()
        await self.engine.dispose()

    async def test_ticket_is_signed_owner_scoped_and_contains_only_safe_fact_fields(self):
        result = await self.service.create_mini_site_stamp_ticket(self.user_id, ["earned-stamp"])
        claims = jwt.decode(
            result["ticket"], JWT_SECRET, algorithms=[JWT_ALG],
            audience="crista-suitcase-mini-site", issuer="crista-ai-agent",
        )
        self.assertEqual(self.user_id, claims["sub"])
        self.assertEqual("trip-mini-site-stamps", claims["purpose"])
        self.assertEqual(result["stamps"], claims["stamps"])
        self.assertEqual("The verified fact.", result["stamps"][0]["fact"])
        self.assertEqual("https://example.test/fact", result["stamps"][0]["source_url"])

    async def test_ticket_refuses_stamps_owned_by_another_user_or_unknown_keys(self):
        for user_id, key in ((self.other_user_id, "earned-stamp"), (self.user_id, "missing-stamp")):
            with self.assertRaises(ValueError):
                await self.service.create_mini_site_stamp_ticket(user_id, [key])


if __name__ == "__main__":
    unittest.main()
