from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Index, UniqueConstraint, ForeignKey, Boolean

from app.db.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "app_user"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID/ULID
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auth_provider: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 'password', 'google', 'github', ...
    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")  # type: ignore

    __table_args__ = (
        Index("idx_user_email", "email"),
    )

class AccessToken(Base):
    __tablename__ = "access_token"

    token: Mapped[str] = mapped_column(String, primary_key=True)  # храните хэш, а не сырой токен
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # "chat:read chat:write"

    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("idx_access_token_user", "user_id"),
        Index("idx_access_token_expires", "expires_at"),
    )

class OAuthProviderAccount(Base):
    __tablename__ = "oauth_provider_account"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        Index("idx_oauth_user", "user_id"),
    )
