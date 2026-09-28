"""publish the France country Wiki article

Revision ID: ac0b1c2d3e4
Revises: ab0b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ac0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "ab0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-fr"
VERSION_ID = "wiki-country-fr-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "Франция объединяет разные региональные культурные и природные контексты. Понимание конкретного города или территории помогает не сводить страну к одному образу.",
    "history": "В списке Всемирного наследия ЮНЕСКО для Франции есть культурные, природные и смешанные объекты: от археологических и средневековых памятников до городских ансамблей и ландшафтов. У каждого места своя история, поэтому карточка предлагает начинать с его собственных источников и контекста.",
    "cuisine": "Гастрономическая трапеза французов внесена ЮНЕСКО в Репрезентативный список нематериального культурного наследия. Это социальная практика для важных событий, в которой ценятся совместность, выбор продуктов, сочетания блюд и обстановка стола. Региональные рецепты и привычки при этом различаются.",
    "traditions": "Локальные правила и ритм жизни зависят от региона и ситуации. В кафе, на экскурсии или городском событии полезно ориентироваться на информацию организатора и уточнять правила на месте.",
    "practical": [
        {"label": "Валюта", "value": "Евро (EUR)"},
        {"label": "Экстренная помощь", "value": "112 · европейский номер экстренной помощи"},
    ],
}

SOURCES = [
    {"label": "ЮНЕСКО: объекты Всемирного наследия Франции", "url": "https://whc.unesco.org/en/statesparties/fr"},
    {"label": "ЮНЕСКО: гастрономическая трапеза французов", "url": "https://ich.unesco.org/en/lists?RL=00437"},
    {"label": "Еврокомиссия: Франция и евро", "url": "https://economy-finance.ec.europa.eu/euro/eu-countries-and-euro/france-and-euro_en"},
    {"label": "Service-Public.fr: номера экстренной помощи", "url": "https://lannuaire.service-public.fr/?lang=fr"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-fr", "published_version_id": None,
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
        "status": "published", "title": "Франция", "body": BODY, "sources": SOURCES,
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
