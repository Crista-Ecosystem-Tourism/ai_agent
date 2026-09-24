from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.wiki import WikiArticle, WikiArticleVersion
from app.db.models.auth import User


class WikiNotFoundError(RuntimeError):
    pass


class WikiService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_published(self, slug: str, language: str = "ru") -> dict[str, Any]:
        async with self.session_factory() as db:
            candidates = [(f"{slug}-en", "en"), (slug, "ru")] if language == "en" else [(slug, "ru")]
            article = None
            version = None
            content_language = "ru"
            for candidate_slug, candidate_language in candidates:
                candidate = await db.scalar(select(WikiArticle).where(WikiArticle.slug == candidate_slug))
                if candidate is None or candidate.published_version_id is None:
                    continue
                published = await db.get(WikiArticleVersion, candidate.published_version_id)
                if published is None or published.status != "published":
                    continue
                article, version, content_language = candidate, published, candidate_language
                break
            if article is None or version is None:
                raise WikiNotFoundError(slug)
            result = self._public_version(article, version)
            result["slug"] = slug
            result["content_language"] = content_language
            return result

    async def get_published_version(self, version_id: str) -> dict[str, Any]:
        async with self.session_factory() as db:
            version = await db.get(WikiArticleVersion, version_id)
            if version is None or version.status != "published":
                raise WikiNotFoundError(version_id)
            article = await db.get(WikiArticle, version.article_id)
            if article is None:
                raise WikiNotFoundError(version_id)
            return self._public_version(article, version)

    async def list_authored(self, user_id: str) -> list[dict[str, Any]]:
        async with self.session_factory() as db:
            rows = (await db.execute(
                select(WikiArticle, WikiArticleVersion)
                .join(WikiArticleVersion, WikiArticleVersion.article_id == WikiArticle.id)
                .where(WikiArticleVersion.author_id == user_id)
                .order_by(WikiArticleVersion.updated_at.desc())
            )).all()
            return [self._author_version(article, version) for article, version in rows]

    async def list_review_queue(self, editor_id: str) -> list[dict[str, Any]]:
        async with self.session_factory() as db:
            editor = await db.get(User, editor_id)
            if editor is None or not editor.is_editor:
                raise PermissionError("Требуется роль редактора Wiki")
            rows = (await db.execute(
                select(WikiArticle, WikiArticleVersion)
                .join(WikiArticleVersion, WikiArticleVersion.article_id == WikiArticle.id)
                .where(WikiArticleVersion.status == "review")
                .order_by(WikiArticleVersion.updated_at.asc())
            )).all()
            return [self._author_version(article, version) for article, version in rows]

    async def create_draft(
        self, user_id: str, slug: str, title: str, body: dict[str, Any], sources: list[dict[str, str]], license_name: str,
    ) -> dict[str, Any]:
        async with self.session_factory() as db:
            article = await db.scalar(select(WikiArticle).where(WikiArticle.slug == slug))
            now = datetime.now(timezone.utc)
            if article is None:
                article = WikiArticle(id=uuid.uuid4().hex, slug=slug, created_at=now, updated_at=now)
                db.add(article)
            version = WikiArticleVersion(
                id=uuid.uuid4().hex,
                article_id=article.id,
                author_id=user_id,
                status="draft",
                title=title,
                body=body,
                sources=sources,
                license=license_name,
                created_at=now,
                updated_at=now,
            )
            db.add(version)
            await db.commit()
            return self._author_version(article, version)

    async def submit_for_review(self, user_id: str, version_id: str) -> dict[str, Any]:
        async with self.session_factory() as db:
            version = await db.get(WikiArticleVersion, version_id)
            if version is None or version.author_id != user_id:
                raise WikiNotFoundError(version_id)
            if version.status != "draft":
                raise ValueError("Версия уже отправлена или опубликована")
            version.status = "review"
            version.updated_at = datetime.now(timezone.utc)
            article = await db.get(WikiArticle, version.article_id)
            if article is None:
                raise WikiNotFoundError(version.article_id)
            await db.commit()
            return self._author_version(article, version)

    async def publish_reviewed(self, editor_id: str, version_id: str) -> dict[str, Any]:
        async with self.session_factory() as db:
            editor = await db.get(User, editor_id)
            if editor is None or not editor.is_editor:
                raise PermissionError("Требуется роль редактора Wiki")
            version = await db.get(WikiArticleVersion, version_id)
            if version is None:
                raise WikiNotFoundError(version_id)
            if version.status != "review":
                raise ValueError("Опубликовать можно только версию на review")
            article = await db.get(WikiArticle, version.article_id)
            if article is None:
                raise WikiNotFoundError(version.article_id)
            now = datetime.now(timezone.utc)
            version.status = "published"
            version.reviewed_at = now
            version.published_at = now
            version.updated_at = now
            article.published_version_id = version.id
            article.updated_at = now
            await db.commit()
            return self._public_version(article, version)

    @staticmethod
    def _public_version(article: WikiArticle, version: WikiArticleVersion) -> dict[str, Any]:
        return {
            "version_id": version.id,
            "slug": article.slug,
            "title": version.title,
            "body": version.body,
            "sources": version.sources,
            "license": version.license,
            "published_at": version.published_at.isoformat() if version.published_at else None,
        }

    @staticmethod
    def _author_version(article: WikiArticle, version: WikiArticleVersion) -> dict[str, Any]:
        return {
            "id": version.id,
            "slug": article.slug,
            "status": version.status,
            "title": version.title,
            "body": version.body,
            "sources": version.sources,
            "license": version.license,
            "updated_at": version.updated_at.isoformat(),
        }
