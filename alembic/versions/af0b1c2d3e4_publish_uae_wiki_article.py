"""publish the United Arab Emirates country Wiki article

Revision ID: af0b1c2d3e4
Revises: ae0b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "af0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "ae0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-ae"
VERSION_ID = "wiki-country-ae-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "ОАЭ объединяют наследие оазисов, археологические ландшафты и современные города. Уважительное знакомство с ними требует учитывать местный контекст и правила конкретного эмирата или площадки.",
    "history": "В список Всемирного наследия ЮНЕСКО для ОАЭ входят культурные территории Аль-Айна и палеоландшафт Файя, а также природный объект Вади-Вурайя. Эти места показывают разные слои истории и природного наследия страны; для каждой площадки важны её собственные правила посещения и сохранения.",
    "cuisine": "Кухня и практики гостеприимства имеют региональный контекст. В списках нематериального культурного наследия ЮНЕСКО для ОАЭ есть блюдо харис; это пример одной живой пищевой практики, который не заменяет разнообразие местных традиций.",
    "traditions": "Аль-Айяла — совместная традиционная исполнительская практика ОАЭ и Омана, внесённая ЮНЕСКО в Репрезентативный список. Она соединяет поэтическое пение, барабаны и танец и исполняется на свадьбах и других праздничных событиях.",
    "practical": [
        {"label": "Валюта", "value": "Дирхам ОАЭ (AED)"},
        {"label": "Экстренная помощь", "value": "999 · полиция; 998 · скорая; 997 · пожарная служба"},
    ],
}

SOURCES = [
    {"label": "ЮНЕСКО: объекты Всемирного наследия ОАЭ", "url": "https://whc.unesco.org/en/statesparties/ae"},
    {"label": "ЮНЕСКО: нематериальное наследие ОАЭ", "url": "https://ich.unesco.org/en/state/united-arab-emirates-AE?info=elements-on-the-lists"},
    {"label": "ЮНЕСКО: Аль-Айяла", "url": "https://ich.unesco.org/en/RL/al-ayyala-a-traditional-performing-art-of-the-sultanate-of-oman-and-the-united-arab-emirates-01012?RL=01012"},
    {"label": "Центральный банк ОАЭ: единица валюты", "url": "https://rulebook.centralbank.ae/en/rulebook/article-52-currency-unit"},
    {"label": "Правительство ОАЭ: экстренные номера", "url": "https://u.ae/en//information-and-services/justice-safety-and-the-law/handling-emergencies"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-ae", "published_version_id": None,
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
        "status": "published", "title": "ОАЭ", "body": BODY, "sources": SOURCES,
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
