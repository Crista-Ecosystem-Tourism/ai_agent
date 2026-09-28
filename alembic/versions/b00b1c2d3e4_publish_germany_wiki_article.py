"""publish the Germany country Wiki article

Revision ID: b00b1c2d3e4
Revises: af0b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b00b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "af0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-de"
VERSION_ID = "wiki-country-de-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "Германия объединяет региональные культурные ландшафты, исторические города и природные территории. Контекст конкретной земли или города помогает точнее читать это разнообразие.",
    "history": "В списке Всемирного наследия ЮНЕСКО для Германии есть исторические города, соборы, архитектурные ансамбли, индустриальное наследие и природные объекты. Они относятся к разным периодам и регионам, поэтому одна история не описывает страну целиком.",
    "cuisine": "Кулинарные традиции различаются между регионами. Полезно узнавать у заведения происхождение блюда, сезонность продуктов и локальный способ подачи вместо того, чтобы считать один рецепт общим для всей страны.",
    "traditions": "Органное мастерство и музыка внесены ЮНЕСКО в Репрезентативный список нематериального культурного наследия. Инструменты создаются для конкретных архитектурных пространств, а знания передаются через работу с мастером, профессиональные школы и университеты.",
    "practical": [
        {"label": "Валюта", "value": "Евро (EUR)"},
        {"label": "Экстренная помощь", "value": "112 · пожарная и спасательная службы"},
    ],
}

SOURCES = [
    {"label": "ЮНЕСКО: объекты Всемирного наследия Германии", "url": "https://whc.unesco.org/en/statesparties/de"},
    {"label": "ЮНЕСКО: органное мастерство и музыка", "url": "https://ich.unesco.org/en/RL/organ-craftsmanship-and-music-01277"},
    {"label": "Еврокомиссия: Германия и евро", "url": "https://economy-finance.ec.europa.eu/euro/eu-countries-and-euro/germany-and-euro_en?prefLang=pt"},
    {"label": "Федеральный портал здоровья: экстренный номер", "url": "https://gesund.bund.de/en/erste-hilfe"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-de", "published_version_id": None,
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
        "status": "published", "title": "Германия", "body": BODY, "sources": SOURCES,
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
