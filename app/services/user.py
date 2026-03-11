import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, insert, func
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
                select(User.id, User.email, User.name, User.is_active)
                .where(User.id == user_id)
            )).first()

            if not row:
                return None

            return {
                "id": row.id,
                "email": row.email,
                "name": row.name,
                "is_active": row.is_active
            }

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email (case-insensitive)."""
        async with self.session_factory() as db:
            row = (await db.execute(
                select(User).where(func.lower(User.email) == email.lower())
            )).scalar_one_or_none()
            return row

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
