from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, insert
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
