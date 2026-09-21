"""seed Moscow Wiki article

Revision ID: i8d9e0f1a2b3
Revises: h7c8d9e0f1a2
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "i8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "h7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.execute(sa.text("""
        INSERT INTO app_user (id, email, name, is_active, is_editor, auth_provider, created_at, updated_at)
        VALUES ('crista-editorial', NULL, 'Редакция Crista', FALSE, TRUE, 'system', :now, :now)
        ON CONFLICT (id) DO NOTHING
    """).bindparams(now=now))
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": "wiki-moscow", "slug": "moscow", "published_version_id": None,
        "created_at": now, "updated_at": now,
    }])
    op.bulk_insert(sa.table(
        "wiki_article_version",
        sa.column("id", sa.String()), sa.column("article_id", sa.String()), sa.column("author_id", sa.String()),
        sa.column("status", sa.String()), sa.column("title", sa.String()), sa.column("body", postgresql.JSONB()),
        sa.column("sources", postgresql.JSONB()), sa.column("license", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)), sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": "wiki-moscow-v1", "article_id": "wiki-moscow", "author_id": "crista-editorial",
        "status": "published", "title": "Москва", "license": "CC BY 4.0",
        "body": {
            "summary": "Москва — столица России и город, где исторические районы, транспорт и культурные институции складываются в один маршрут.",
            "sections": [
                {"title": "Кремль и Красная площадь", "text": "Историческое ядро города объединяет Кремль, Соборную площадь и Красную площадь."},
                {"title": "Городской маршрут", "text": "В игровом маршруте Crista факты о Москве связываются с первоисточниками и проверяемыми заданиями."},
            ],
        },
        "sources": [
            {"label": "Официальный сайт Московского Кремля", "url": "https://www.kreml.ru/"},
            {"label": "Московский метрополитен: история", "url": "https://mosmetro.ru/about/history"},
        ],
        "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    }])
    op.execute(sa.text("UPDATE wiki_article SET published_version_id = 'wiki-moscow-v1' WHERE id = 'wiki-moscow'"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM wiki_article_version WHERE id = 'wiki-moscow-v1'"))
    op.execute(sa.text("DELETE FROM wiki_article WHERE id = 'wiki-moscow'"))
    op.execute(sa.text("DELETE FROM app_user WHERE id = 'crista-editorial'"))
