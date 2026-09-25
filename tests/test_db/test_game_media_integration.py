import io
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Register all FK targets before constructing SQLAlchemy mappers.
from app.db.models import auth, chat, game, media  # noqa: F401
from app.db.dsn import get_database_url
from app.db.models.auth import User
from app.db.models.media import GameMediaAsset
from app.core.media_storage import LocalPrivateMediaStorage
from app.services.media import MediaNotFoundError, MediaService


def make_png() -> bytes:
    image = Image.new("RGB", (32, 24), "navy")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class GameMediaIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Run against an already-migrated disposable PostgreSQL database with game seeds."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(get_database_url())
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.owner_id = uuid.uuid4().hex
        self.other_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add_all([
                User(id=self.owner_id, email=f"media-owner-{self.owner_id}@example.test", name="Owner", is_active=True, auth_provider="test", created_at=now, updated_at=now),
                User(id=self.other_id, email=f"media-other-{self.other_id}@example.test", name="Other", is_active=True, auth_provider="test", created_at=now, updated_at=now),
            ])
            await db.commit()
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = LocalPrivateMediaStorage(self.tempdir.name)
        self.media = MediaService(self.sessions, self.storage)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.tempdir.cleanup()

    async def test_owner_scoped_quest_media_round_trip_and_delete(self):
        created = await self.media.upload(self.owner_id, "moscow-red-square", make_png())
        self.assertEqual(created["quest_id"], "moscow-red-square")
        self.assertEqual(created["content_type"], "image/jpeg")
        self.assertEqual(created["visibility"], "private")
        self.assertEqual(created["exif"], "stripped")
        self.assertEqual(created["width"], 32)
        self.assertEqual(created["height"], 24)

        mine = await self.media.list_mine(self.owner_id)
        self.assertEqual([asset["id"] for asset in mine], [created["id"]])
        with Image.open(io.BytesIO(await self.media.read_mine(self.owner_id, created["id"]))) as stored:
            self.assertEqual(stored.format, "JPEG")
            self.assertEqual(stored.size, (32, 24))
        self.assertGreater(len(await self.media.read_mine(self.owner_id, created["id"], preview=True)), 0)

        with self.assertRaises(MediaNotFoundError):
            await self.media.read_mine(self.other_id, created["id"])
        with self.assertRaises(MediaNotFoundError):
            await self.media.delete_mine(self.other_id, created["id"])

        async with self.sessions() as db:
            row = await db.scalar(select(GameMediaAsset).where(GameMediaAsset.id == created["id"]))
            self.assertIsNotNone(row)
            storage_key = row.storage_key

        await self.media.delete_mine(self.owner_id, created["id"])
        self.assertEqual(await self.media.list_mine(self.owner_id), [])
        with self.assertRaises(MediaNotFoundError):
            await self.media.read_mine(self.owner_id, created["id"])
        self.assertFalse((Path(self.tempdir.name) / f"{storage_key}.jpg").exists())
        self.assertFalse((Path(self.tempdir.name) / f"{storage_key}-preview.jpg").exists())


if __name__ == "__main__":
    unittest.main()
