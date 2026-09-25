import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Register relationship targets before SQLAlchemy configures User mappings.
from app.db.models import chat, game, tip  # noqa: F401
from app.db.dsn import get_database_url
from app.db.models.auth import User
from app.services.tips import TipDuplicateReportError, TipPermissionError, TipRateLimitError, TipService


class GameTipModerationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Runs against a migrated disposable PostgreSQL database with published game seeds."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(get_database_url())
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.author_id = uuid.uuid4().hex
        self.reporter_id = uuid.uuid4().hex
        self.editor_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add_all([
                User(id=self.author_id, email=f"tip-author-{self.author_id}@example.test", name="Author", is_active=True, auth_provider="test", created_at=now, updated_at=now),
                User(id=self.reporter_id, email=f"tip-reporter-{self.reporter_id}@example.test", name="Reporter", is_active=True, auth_provider="test", created_at=now, updated_at=now),
                User(id=self.editor_id, email=f"tip-editor-{self.editor_id}@example.test", name="Editor", is_active=True, is_editor=True, auth_provider="test", created_at=now, updated_at=now),
            ])
            await db.commit()
        self.tips = TipService(self.sessions)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_draft_review_public_report_hide_and_audit(self):
        draft = await self.tips.create_draft(self.author_id, "moscow-red-square", "Wear comfortable shoes for the square.")
        edited = await self.tips.update_draft(self.author_id, draft["id"], "Bring comfortable shoes for the square.")
        self.assertEqual(edited["status"], "draft")
        submitted = await self.tips.submit(self.author_id, draft["id"])
        self.assertEqual(submitted["status"], "review")
        self.assertEqual(len(await self.tips.list_review_queue(self.editor_id)), 1)

        with self.assertRaises(TipPermissionError):
            await self.tips.list_review_queue(self.author_id)

        published = await self.tips.decide(self.editor_id, draft["id"], "publish", "Location tip checked.")
        self.assertEqual(published["status"], "published")
        public_tips = await self.tips.list_published("moscow-red-square")
        self.assertEqual([tip["id"] for tip in public_tips], [draft["id"]])
        self.assertNotIn("decision_note", public_tips[0])

        report = await self.tips.report(self.reporter_id, draft["id"], "inaccurate", "Please verify the hours.")
        with self.assertRaises(TipDuplicateReportError):
            await self.tips.report(self.reporter_id, draft["id"], "other")
        self.assertEqual(len(await self.tips.list_reports(self.editor_id)), 1)
        resolved = await self.tips.resolve_report(self.editor_id, report["id"], "hide_tip", "Temporarily hidden for review.")
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(await self.tips.list_published("moscow-red-square"), [])

        audit = await self.tips.list_audit(self.editor_id)
        actions = {entry["action"] for entry in audit}
        self.assertTrue({"draft_created", "draft_updated", "submitted_for_review", "tip_publish", "tip_reported", "tip_hidden", "report_hide_tip"} <= actions)

    async def test_submission_rate_limit_is_per_user_and_rolling_day(self):
        for index in range(5):
            draft = await self.tips.create_draft(self.author_id, "moscow-red-square", f"Small useful location note number {index}.")
            await self.tips.submit(self.author_id, draft["id"])
        sixth = await self.tips.create_draft(self.author_id, "moscow-red-square", "Another useful location note number six.")
        with self.assertRaises(TipRateLimitError):
            await self.tips.submit(self.author_id, sixth["id"])


if __name__ == "__main__":
    unittest.main()
