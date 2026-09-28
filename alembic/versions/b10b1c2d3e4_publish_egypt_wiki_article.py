"""publish the Egypt country Wiki article

Revision ID: b10b1c2d3e4
Revises: b00b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b10b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "b00b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-eg"
VERSION_ID = "wiki-country-eg-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "Египет объединяет древние археологические комплексы, исторические города, пустынные и речные ландшафты. Контекст конкретной территории важнее единого образа страны.",
    "history": "В списке Всемирного наследия ЮНЕСКО для Египта есть Мемфис и пирамидные поля от Гизы до Дахшура, древние Фивы, исторический Каир, нубийские памятники и природная Долина китов. Это разные эпохи и типы наследия, поэтому к каждому месту нужен собственный исторический и природоохранный контекст.",
    "cuisine": "Кулинарные привычки различаются между регионами и семьями. При знакомстве с блюдом полезно уточнять состав, способ приготовления и локальный контекст у самого заведения или организатора.",
    "traditions": "Тахтиб — игра с палками, внесённая ЮНЕСКО в Репрезентативный список нематериального культурного наследия. Исторически связанная с боевыми практиками, сегодня она исполняется как праздничная игра: удары не допускаются, а правила опираются на взаимное уважение и самоконтроль.",
    "practical": [
        {"label": "Валюта", "value": "Египетский фунт (EGP)"},
        {"label": "Экстренная помощь", "value": "122 · полиция; 123 · скорая; 180 · пожарная служба"},
    ],
}

SOURCES = [
    {"label": "ЮНЕСКО: объекты Всемирного наследия Египта", "url": "https://whc.unesco.org/en/statesparties/eg/"},
    {"label": "ЮНЕСКО: тахтиб, игра с палками", "url": "https://ich.unesco.org/en/RL/tahteeb-stick-game-01189"},
    {"label": "Центральный банк Египта: расчёты в египетских фунтах", "url": "https://www.cbe.org.eg/en/payment-systems-and-services/payment-systems/cheque-clearing-house-cch/egp-cch"},
    {"label": "Государственный справочник Кафр-эш-Шейха: экстренные номера", "url": "https://kfs.gov.eg/index.php/directory"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-eg", "published_version_id": None,
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
        "status": "published", "title": "Египет", "body": BODY, "sources": SOURCES,
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
