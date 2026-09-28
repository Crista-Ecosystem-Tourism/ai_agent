"""publish the Italy country Wiki article

Revision ID: ab0b1c2d3e4
Revises: aa0b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ab0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "aa0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-it"
VERSION_ID = "wiki-country-it-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "Италия объединяет разные региональные культуры. История, искусство и кухня здесь лучше читаются через контекст конкретного города или региона.",
    "history": "Итальянская культурная карта включает археологические места Рима и Помпей, города искусства, исторические поселения и объекты ЮНЕСКО. Эти пласты не сводятся к одному периоду: при знакомстве с местом полезно смотреть на его собственную историю и локальные источники.",
    "cuisine": "Итальянская кухня строится на региональном разнообразии: у регионов, городов и семей есть свои интерпретации рецептов. Официальный туристический портал связывает это разнообразие с разными ландшафтами, долгой культурной историей и местными продуктами.",
    "traditions": "Обычаи, ремёсла и праздники различаются между регионами. Уважительный способ знакомиться с местной традицией — уточнять правила у площадки или организатора и не считать один городской опыт универсальным для всей страны.",
    "practical": [
        {"label": "Валюта", "value": "Евро (EUR)"},
        {"label": "Экстренная помощь", "value": "112 · единый номер экстренной помощи"},
    ],
}

SOURCES = [
    {"label": "Italia.it: искусство и культура Италии", "url": "https://www.italia.it/en/italy/things-to-do/art-culture"},
    {"label": "Italia.it: итальянская кухня и региональные традиции", "url": "https://www.italia.it/en/italy/things-to-do/italian-cuisine-unesco-heritage"},
    {"label": "Еврокомиссия: Италия и евро", "url": "https://economy-finance.ec.europa.eu/euro/eu-countries-and-euro/italy-and-euro_en"},
    {"label": "Правительство Италии: единый номер 112", "url": "https://www.affarieuropei.gov.it/media/3289/scarica-la-brochure-sul-112.pdf"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-it", "published_version_id": None,
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
        "status": "published", "title": "Италия", "body": BODY, "sources": SOURCES,
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
