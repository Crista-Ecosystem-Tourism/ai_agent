"""publish the Thailand country Wiki article

Revision ID: ae0b1c2d3e4
Revises: ad0b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ae0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "ad0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-th"
VERSION_ID = "wiki-country-th-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "Таиланд сочетает исторические города, природные территории и живые культурные практики. Для осмысленного знакомства с местом важны его региональный и местный контекст.",
    "history": "В списке Всемирного наследия ЮНЕСКО для Таиланда есть культурные и природные объекты: исторические города Аюттхая и Сукхотай, археологические памятники и охраняемые лесные комплексы. У каждого из них свой период и способ сохранения, поэтому страна не сводится к одной исторической линии.",
    "cuisine": "Кулинарные традиции различаются между регионами. ЮНЕСКО относит том ям кунг к элементам нематериального культурного наследия Таиланда; это один из примеров живой практики, который не заменяет разнообразие местных кухонь.",
    "traditions": "Кхон — тайская масочная танцевальная драма, внесённая ЮНЕСКО в Репрезентативный список. В этом искусстве соединяются музыка, вокал, литература, танец, ритуал и ремесло; сегодня оно передаётся в том числе через образовательные учреждения и творческие клубы.",
    "practical": [
        {"label": "Валюта", "value": "Тайский бат (THB)"},
        {"label": "Туристическая полиция", "value": "1155 · помощь туристам"},
    ],
}

SOURCES = [
    {"label": "ЮНЕСКО: объекты Всемирного наследия Таиланда", "url": "https://whc.unesco.org/en/statesparties/th"},
    {"label": "ЮНЕСКО: нематериальное наследие Таиланда", "url": "https://ich.unesco.org/en/state/thailand-TH"},
    {"label": "ЮНЕСКО: кхон, масочная танцевальная драма", "url": "https://ich.unesco.org/en/RL/khon-masked-dance-drama-in-thailand-01385"},
    {"label": "Банк Таиланда: валюта и единица бата", "url": "https://www.bot.or.th/content/dam/bot/documents/en/laws-and-rules/laws-and-regulations/legal-department/2-currency-act/2.1%20LAW02_CurrencyAct.pdf"},
    {"label": "Tourism Authority of Thailand: туристическая полиция", "url": "https://www.tourismthailand.org/Articles/tourist-police-app-en"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-th", "published_version_id": None,
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
        "status": "published", "title": "Таиланд", "body": BODY, "sources": SOURCES,
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
