"""publish the Spain country Wiki article

Revision ID: ad0b1c2d3e4
Revises: ac0b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ad0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "ac0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-es"
VERSION_ID = "wiki-country-es-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "Испания объединяет разные региональные культурные и природные контексты. Знакомство с конкретной территорией помогает увидеть их разнообразие без упрощений.",
    "history": "В списке Всемирного наследия ЮНЕСКО для Испании есть культурные, природные и смешанные объекты: археологические комплексы, исторические города, архитектурные ансамбли и национальные парки. Контекст конкретного места важнее общего шаблона о стране.",
    "cuisine": "Кухня Испании различается между регионами и опирается на местные продукты и традиции. При знакомстве с блюдом полезно узнавать его регион происхождения и способ подачи у самого заведения или организатора.",
    "traditions": "Фламенко внесено ЮНЕСКО в Репрезентативный список нематериального культурного наследия. Это художественное выражение, объединяющее пение, танец и гитарное сопровождение; его центр — Андалусия, при этом традиция имеет связи и с другими регионами. Фламенко — одна из живых практик, а не универсальное описание всей страны.",
    "practical": [
        {"label": "Валюта", "value": "Евро (EUR)"},
        {"label": "Экстренная помощь", "value": "112 · единый номер экстренной помощи"},
    ],
}

SOURCES = [
    {"label": "ЮНЕСКО: объекты Всемирного наследия Испании", "url": "https://whc.unesco.org/en/statesparties/es"},
    {"label": "ЮНЕСКО: фламенко", "url": "https://ich.unesco.org/es/RL/el-flamenco-00363"},
    {"label": "Еврокомиссия: Испания и евро", "url": "https://economy-finance.ec.europa.eu/euro/eu-countries-and-euro/spain-and-euro_en"},
    {"label": "112 Spain: единый экстренный номер", "url": "https://www.112.es/"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-es", "published_version_id": None,
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
        "id": VERSION_ID, "article_id": ARTICLE_ID, "author_id": AUTHOR_ID,
        "status": "published", "title": "Испания", "body": BODY, "sources": SOURCES,
        "license": "CC BY 4.0", "reviewed_at": now, "published_at": now,
        "created_at": now, "updated_at": now,
    }])
    op.execute(sa.text(
        "UPDATE wiki_article SET published_version_id = :version_id WHERE id = :article_id"
    ).bindparams(version_id=VERSION_ID, article_id=ARTICLE_ID))


def downgrade() -> None:
    op.execute(sa.text(
        "UPDATE wiki_article SET published_version_id = NULL WHERE id = :article_id"
    ).bindparams(article_id=ARTICLE_ID))
    op.execute(sa.text(
        "DELETE FROM wiki_article_version WHERE id = :version_id"
    ).bindparams(version_id=VERSION_ID))
    op.execute(sa.text(
        "DELETE FROM wiki_article WHERE id = :article_id"
    ).bindparams(article_id=ARTICLE_ID))
