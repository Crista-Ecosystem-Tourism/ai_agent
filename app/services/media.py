from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.media_policy import (
    MAX_ASSETS_PER_USER,
    MAX_USER_STORAGE_BYTES,
    sanitize_image,
)
from app.db.models.auth import User
from app.db.models.game import GameQuest
from app.db.models.media import GameMediaAsset


class MediaNotFoundError(RuntimeError):
    pass


class MediaLimitError(RuntimeError):
    pass


class MediaStorageUnavailable(RuntimeError):
    pass


class LocalPrivateMediaStorage:
    """Private filesystem adapter. The configured directory must be a durable mount."""

    def __init__(self, root: str | None):
        self.root = Path(root).resolve() if root and root.strip() else None

    def require_root(self) -> Path:
        if self.root is None:
            raise MediaStorageUnavailable("Хранилище файлов не настроено")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        return self.root

    def put_pair(self, key: str, original: bytes, preview: bytes) -> None:
        root = self.require_root()
        (root / f"{key}.jpg").write_bytes(original)
        try:
            (root / f"{key}-preview.jpg").write_bytes(preview)
        except Exception:
            (root / f"{key}.jpg").unlink(missing_ok=True)
            raise

    def read(self, key: str) -> bytes:
        return (self.require_root() / f"{key}.jpg").read_bytes()

    def delete_pair(self, key: str) -> None:
        if self.root is None:
            return
        (self.root / f"{key}.jpg").unlink(missing_ok=True)
        (self.root / f"{key}-preview.jpg").unlink(missing_ok=True)


class MediaService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], storage: LocalPrivateMediaStorage):
        self.session_factory = session_factory
        self.storage = storage

    async def list_mine(self, owner_id: str) -> list[dict]:
        async with self.session_factory() as db:
            assets = (await db.scalars(
                select(GameMediaAsset).where(GameMediaAsset.owner_id == owner_id)
                .order_by(GameMediaAsset.created_at.desc(), GameMediaAsset.id)
            )).all()
            return [self._payload(asset) for asset in assets]

    async def upload(self, owner_id: str, quest_id: str, raw: bytes) -> dict:
        sanitized = sanitize_image(raw)
        self.storage.require_root()
        asset_id = uuid.uuid4().hex
        key = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            user = await db.scalar(select(User).where(User.id == owner_id).with_for_update())
            if user is None:
                raise MediaNotFoundError
            quest = await db.scalar(select(GameQuest).where(GameQuest.id == quest_id))
            if quest is None:
                raise MediaNotFoundError
            count, used = (await db.execute(
                select(func.count(GameMediaAsset.id), func.coalesce(func.sum(GameMediaAsset.byte_size), 0))
                .where(GameMediaAsset.owner_id == owner_id)
            )).one()
            if count >= MAX_ASSETS_PER_USER or used + len(sanitized.original) > MAX_USER_STORAGE_BYTES:
                raise MediaLimitError
            self.storage.put_pair(key, sanitized.original, sanitized.preview)
            asset = GameMediaAsset(
                id=asset_id, owner_id=owner_id, quest_id=quest_id, storage_key=key,
                preview_key=key, content_type="image/jpeg", byte_size=len(sanitized.original),
                width=sanitized.width, height=sanitized.height,
                sha256=hashlib.sha256(sanitized.original).hexdigest(), created_at=now,
            )
            db.add(asset)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                self.storage.delete_pair(key)
                raise
            return self._payload(asset)

    async def read_mine(self, owner_id: str, asset_id: str, preview: bool = False) -> bytes:
        async with self.session_factory() as db:
            asset = await db.scalar(select(GameMediaAsset).where(
                GameMediaAsset.id == asset_id, GameMediaAsset.owner_id == owner_id,
            ))
            if asset is None:
                raise MediaNotFoundError
            key = asset.preview_key if preview else asset.storage_key
        try:
            return self.storage.read(f"{key}-preview" if preview else key)
        except FileNotFoundError as error:
            raise MediaStorageUnavailable("Файл временно недоступен") from error

    async def delete_mine(self, owner_id: str, asset_id: str) -> None:
        async with self.session_factory() as db:
            asset = await db.scalar(select(GameMediaAsset).where(
                GameMediaAsset.id == asset_id, GameMediaAsset.owner_id == owner_id,
            ).with_for_update())
            if asset is None:
                raise MediaNotFoundError
            key = asset.storage_key
            await db.delete(asset)
            await db.commit()
        self.storage.delete_pair(key)

    @staticmethod
    def _payload(asset: GameMediaAsset) -> dict:
        return {
            "id": asset.id, "quest_id": asset.quest_id, "content_type": asset.content_type,
            "byte_size": asset.byte_size, "width": asset.width, "height": asset.height,
            "created_at": asset.created_at.isoformat(), "exif": "stripped",
            "visibility": "private", "preview_url": f"/media/{asset.id}/preview",
            "file_url": f"/media/{asset.id}/file",
        }
