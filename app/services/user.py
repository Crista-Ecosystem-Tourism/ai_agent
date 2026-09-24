import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, insert, func, update
from app.db.models.auth import User


class UserService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_or_create_from_google(
        self,
        google_sub: str,
        email: str,
        name: Optional[str] = None
    ) -> str:
        async with self.session_factory() as db:
            user = (await db.execute(
                select(User.id).where(User.id == google_sub)
            )).scalar_one_or_none()

            if user:
                return user

            now = datetime.now(timezone.utc)
            await db.execute(
                insert(User).values(
                    id=google_sub,
                    email=email,
                    name=name,
                    auth_provider="google",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            await db.commit()
            return google_sub

    async def get_by_id(self, user_id: str) -> Optional[dict]:
        async with self.session_factory() as db:
            row = (await db.execute(
                select(User.id, User.email, User.name, User.is_active, User.is_editor)
                .where(User.id == user_id)
            )).first()

            if not row:
                return None

            return {
                "id": row.id,
                "email": row.email,
                "name": row.name,
                "is_active": row.is_active,
                "is_editor": row.is_editor,
            }

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email (case-insensitive)."""
        async with self.session_factory() as db:
            row = (await db.execute(
                select(User).where(func.lower(User.email) == email.lower())
            )).scalar_one_or_none()
            return row

    async def get_vision_consent(self, user_id: str) -> Optional[dict]:
        async with self.session_factory() as db:
            row = (await db.execute(
                select(User.vision_consent_granted, User.vision_consent_version)
                .where(User.id == user_id)
            )).one_or_none()
            if row is None:
                return None
            return {"granted": row.vision_consent_granted, "policy_version": row.vision_consent_version}

    async def get_preferences(self, user_id: str) -> Optional[dict]:
        async with self.session_factory() as db:
            row = (await db.execute(
                select(User.preferred_theme, User.preferred_language).where(User.id == user_id)
            )).one_or_none()
            if row is None:
                return None
            return {"theme": row.preferred_theme, "language": row.preferred_language}

    async def set_preferences(self, user_id: str, theme: str, language: str) -> Optional[dict]:
        async with self.session_factory() as db:
            result = await db.execute(
                update(User).where(User.id == user_id).values(
                    preferred_theme=theme,
                    preferred_language=language,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            if result.rowcount != 1:
                return None
            await db.commit()
        return {"theme": theme, "language": language}

    async def set_vision_consent(self, user_id: str, granted: bool, policy_version: str) -> Optional[dict]:
        async with self.session_factory() as db:
            result = await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    vision_consent_granted=granted,
                    vision_consent_version=policy_version,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            if result.rowcount != 1:
                return None
            await db.commit()
        return {"granted": granted, "policy_version": policy_version}

    async def create_with_password(
        self, email: str, name: str, hashed_password: str
    ) -> User:
        """Create a new user with email/password authentication."""
        async with self.session_factory() as db:
            now = datetime.now(timezone.utc)
            user_id = uuid.uuid4().hex
            await db.execute(
                insert(User).values(
                    id=user_id,
                    email=email.lower(),
                    name=name,
                    hashed_password=hashed_password,
                    auth_provider="password",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            await db.commit()

            user = (await db.execute(
                select(User).where(User.id == user_id)
            )).scalar_one()
            return user
