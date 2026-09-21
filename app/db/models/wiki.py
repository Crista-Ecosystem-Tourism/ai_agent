from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class WikiArticle(Base, TimestampMixin):
    __tablename__ = "wiki_article"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    published_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("wiki_article_version.id", use_alter=True, name="fk_wiki_article_published_version"),
        nullable=True,
    )


class WikiArticleVersion(Base, TimestampMixin):
    __tablename__ = "wiki_article_version"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("wiki_article.id"), nullable=False)
    author_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    license: Mapped[str] = mapped_column(String, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("article_id", "id", name="uq_wiki_version_article_id"),
        Index("idx_wiki_version_article_status", "article_id", "status"),
    )
