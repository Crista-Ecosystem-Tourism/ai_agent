from __future__ import annotations

import hashlib
import uuid
import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.media_policy import media_quota_allows, sanitize_media
from app.core.media_storage import MediaStorage, MediaStorageUnavailable
from app.db.models.auth import User
from app.db.models.game import GameQuest
from app.db.models.media import GameMediaAsset


class MediaNotFoundError(RuntimeError):
    pass


class MediaLimitError(RuntimeError):
    pass


class MediaService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], storage: MediaStorage):
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
        sanitized = await asyncio.to_thread(sanitize_media, raw)
        await asyncio.to_thread(self.storage.ensure_available)
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
            if not media_quota_allows(count, used, len(sanitized.original)):
                raise MediaLimitError
            try:
                await asyncio.to_thread(
                    self.storage.put_pair, key, sanitized.original, sanitized.preview, sanitized.content_type,
                )
            except Exception as error:
                raise MediaStorageUnavailable("Хранилище файлов временно недоступно") from error
            asset = GameMediaAsset(
                id=asset_id, owner_id=owner_id, quest_id=quest_id, storage_key=key,
                preview_key=key, content_type=sanitized.content_type, byte_size=len(sanitized.original),
                width=sanitized.width, height=sanitized.height,
                duration_seconds=sanitized.duration_seconds,
                sha256=hashlib.sha256(sanitized.original).hexdigest(), created_at=now,
            )
            db.add(asset)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                try:
                    await asyncio.to_thread(self.storage.delete_pair, key, sanitized.content_type)
                except Exception:
                    pass
                raise
            return self._payload(asset)

    async def read_mine(self, owner_id: str, asset_id: str, preview: bool = False) -> bytes:
        data, _content_type = await self.read_mine_with_type(owner_id, asset_id, preview)
        return data

    async def read_mine_with_type(self, owner_id: str, asset_id: str, preview: bool = False) -> tuple[bytes, str]:
        async with self.session_factory() as db:
            asset = await db.scalar(select(GameMediaAsset).where(
                GameMediaAsset.id == asset_id, GameMediaAsset.owner_id == owner_id,
            ))
            if asset is None:
                raise MediaNotFoundError
            key = asset.preview_key if preview else asset.storage_key
            content_type = "image/jpeg" if preview else asset.content_type
        try:
            data = await asyncio.to_thread(
                self.storage.read, f"{key}-preview" if preview else key, content_type,
            )
            return data, content_type
        except Exception as error:
            raise MediaStorageUnavailable("Файл временно недоступен") from error

    async def delete_mine(self, owner_id: str, asset_id: str) -> None:
        async with self.session_factory() as db:
            asset = await db.scalar(select(GameMediaAsset).where(
                GameMediaAsset.id == asset_id, GameMediaAsset.owner_id == owner_id,
            ).with_for_update())
            if asset is None:
                raise MediaNotFoundError
            key = asset.storage_key
            try:
                await asyncio.to_thread(self.storage.delete_pair, key, asset.content_type)
            except Exception as error:
                raise MediaStorageUnavailable("Не удалось безопасно удалить файл из хранилища") from error
            await db.delete(asset)
            await db.commit()

    @staticmethod
    def _payload(asset: GameMediaAsset) -> dict:
        return {
            "id": asset.id, "quest_id": asset.quest_id, "content_type": asset.content_type,
            "byte_size": asset.byte_size, "width": asset.width, "height": asset.height,
            "duration_seconds": asset.duration_seconds,
            "created_at": asset.created_at.isoformat(), "exif": "stripped",
            "visibility": "private", "preview_url": f"/media/{asset.id}/preview",
            "file_url": f"/media/{asset.id}/file",
        }
