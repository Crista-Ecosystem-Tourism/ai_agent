"""publish an English Moscow Wiki edition without replacing the Russian source

Revision ID: z8f9a0b1c2d3
Revises: z7f8a9b0c1d
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "z8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "z7f8a9b0c1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ARTICLE_ID = "wiki-moscow-en"
ARTICLE_SLUG = "moscow-en"
VERSION_ID = "wiki-moscow-en-v1"
LICENSE = "CC BY 4.0"
ENGLISH_BODY = {
    "summary": "Moscow is Russia’s capital, where historic districts, transport, and cultural institutions come together in one city.",
    "sections": [
        {"title": "The Kremlin and Red Square", "text": "The historic heart of the city brings together the Kremlin, Cathedral Square, and Red Square."},
        {"title": "A route through the city", "text": "Crista’s Moscow route connects local facts to primary sources and questions that can be checked."},
    ],
}
SOURCES = [
    {"label": "Official website of the Moscow Kremlin", "url": "https://www.kreml.ru/"},
    {"label": "Moscow Metro: history", "url": "https://mosmetro.ru/about/history"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": ARTICLE_SLUG, "published_version_id": None,
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
        "id": VERSION_ID, "article_id": ARTICLE_ID, "author_id": "crista-editorial",
        "status": "published", "title": "Moscow", "license": LICENSE,
        "body": ENGLISH_BODY,
        "sources": SOURCES,
        "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    }])
    op.execute(sa.text("UPDATE wiki_article SET published_version_id = :version_id WHERE id = :article_id").bindparams(
        version_id=VERSION_ID, article_id=ARTICLE_ID,
    ))


def downgrade() -> None:
    op.execute(sa.text("UPDATE wiki_article SET published_version_id = NULL WHERE id = :article_id").bindparams(
        article_id=ARTICLE_ID,
    ))
    op.execute(sa.text("DELETE FROM wiki_article_version WHERE id = :version_id").bindparams(version_id=VERSION_ID))
    op.execute(sa.text("DELETE FROM wiki_article WHERE id = :article_id").bindparams(article_id=ARTICLE_ID))
