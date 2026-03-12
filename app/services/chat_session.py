import secrets

from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, insert, update, delete

from app.db.models.chat import ChatSession
from app.core.models import UserPreferences
from app.security.session_secret import hash_secret, verify_secret


class ChatSessionService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def create(self, user_id: Optional[str], title: Optional[str]) -> str:
        session_id = __import__("uuid").uuid4().hex
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)
        async with self.session_factory() as db:
            await db.execute(
                insert(ChatSession).values(
                    id=session_id, user_id=user_id, title=title,
                    is_anonymous=(user_id is None),
                    session_secret_hash=None,
                    created_at=now, updated_at=now, expires_at=expires
                )
            )
            await db.commit()
        return session_id

    async def create_anon(self, title: Optional[str]) -> tuple[str, str]:
        session_id = __import__("uuid").uuid4().hex
        session_secret = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)
        async with self.session_factory() as db:
            await db.execute(
                insert(ChatSession).values(
                    id=session_id,
                    user_id=None,
                    title=title,
                    is_anonymous=True,
                    session_secret_hash=hash_secret(session_secret),
                    created_at=now, updated_at=now, expires_at=expires
                )
            )
            await db.commit()
        return session_id, session_secret
    
    async def get_owner(self, session_id: str) -> Optional[str]:
        async with self.session_factory() as db:
            return (await db.execute(
                select(ChatSession.user_id).where(ChatSession.id == session_id)
            )).scalar_one_or_none()

    async def get_secret_hash(self, session_id: str) -> Optional[bytes]:
        async with self.session_factory() as db:
            return (await db.execute(
                select(ChatSession.session_secret_hash).where(ChatSession.id == session_id)
            )).scalar_one_or_none()

    async def verify_anonymous_access(self, session_id: str, provided_secret: Optional[str]) -> bool:
        async with self.session_factory() as db:
            row = (await db.execute(
                select(ChatSession.is_anonymous, ChatSession.session_secret_hash)
                .where(ChatSession.id == session_id)
            )).first()
            if not row:
                return False
            is_anonymous, secret_hash = row
            if not is_anonymous:
                return True
            return verify_secret(secret_hash, provided_secret or "")

    
    async def attach_owner(self, session_id: str, user_id: str) -> bool:
        async with self.session_factory() as db:
            await db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(user_id=user_id, is_anonymous=False, session_secret_hash=None)
            )
            await db.commit()
            return True
        
    async def get_owned(self, session_id: str, user_id: str) -> Optional[tuple[str, Optional[str]]]:
        async with self.session_factory() as db:
            row = (await db.execute(
                select(ChatSession.id, ChatSession.title, ChatSession.user_id)
                .where(ChatSession.id == session_id)
            )).first()
            if not row or row.user_id != user_id:
                return None
            return (row.id, row.title)

    async def delete_owned(self, session_id: str, user_id: str) -> bool:
        async with self.session_factory() as db:
            owner = (await db.execute(
                select(ChatSession.user_id).where(ChatSession.id == session_id)
            )).scalar_one_or_none()
            if not owner or owner != user_id:
                return False
            await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
            await db.commit()
            return True

    async def list_for_user(self, user_id: str, limit: int = 50):
        async with self.session_factory() as db:
            rows = (await db.execute(
                select(ChatSession.id, ChatSession.title, ChatSession.updated_at)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.updated_at.desc())
                .limit(limit)
            )).all()
            return [{"id": r.id, "title": r.title, "updated_at": r.updated_at.isoformat() if r.updated_at else None} for r in rows]
        
    async def load_preferences(self, session_id: str) -> UserPreferences:
        async with self.session_factory() as db:
            row = (await db.execute(
                select(ChatSession.preferences).where(ChatSession.id == session_id)
            )).scalar_one_or_none()
            if row:
                return UserPreferences(**row)
            return UserPreferences()

    async def save_preferences(self, session_id: str, prefs: UserPreferences) -> None:
        async with self.session_factory() as db:
            await db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(preferences=prefs.model_dump(exclude_none=True))
            )
            await db.commit()

    async def save_place_ratings(self, session_id: str, ratings: dict) -> None:
        async with self.session_factory() as db:
            await db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(place_ratings=ratings)
            )
            await db.commit()

    async def load_place_ratings(self, session_id: str) -> Optional[dict]:
        async with self.session_factory() as db:
            return (await db.execute(
                select(ChatSession.place_ratings).where(ChatSession.id == session_id)
            )).scalar_one_or_none()

    async def save_places_snapshot(self, session_id: str, places: list) -> None:
        async with self.session_factory() as db:
            await db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(places_snapshot=places)
            )
            await db.commit()

    async def load_places_snapshot(self, session_id: str) -> Optional[list]:
        async with self.session_factory() as db:
            return (await db.execute(
                select(ChatSession.places_snapshot).where(ChatSession.id == session_id)
            )).scalar_one_or_none()

    async def save_graph_geojson(self, session_id: str, geojson: dict) -> None:
        async with self.session_factory() as db:
            await db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(graph_geojson=geojson)
            )
            await db.commit()

    async def load_graph_geojson(self, session_id: str) -> Optional[dict]:
        async with self.session_factory() as db:
            return (await db.execute(
                select(ChatSession.graph_geojson).where(ChatSession.id == session_id)
            )).scalar_one_or_none()

    async def update_title(self, session_id: str, title: str) -> None:
        async with self.session_factory() as db:
            await db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(title=title)
            )
            await db.commit()

    async def touch(self, session_id: str):
        async with self.session_factory() as db:
            now = datetime.now(timezone.utc)
            await db.execute(
                update(ChatSession).where(ChatSession.id == session_id).values(updated_at=now)
            )
            await db.commit()
