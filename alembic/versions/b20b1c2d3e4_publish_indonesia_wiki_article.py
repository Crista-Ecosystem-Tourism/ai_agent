"""publish the Indonesia country Wiki article

Revision ID: b20b1c2d3e4
Revises: b10b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b20b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "b10b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-id"
VERSION_ID = "wiki-country-id-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "Индонезия объединяет множество региональных, островных и культурных контекстов. Знакомство с конкретной территорией помогает не сводить их к одному образу.",
    "history": "В списке Всемирного наследия ЮНЕСКО для Индонезии есть храмовые комплексы Боробудур и Прамбанан, культурный ландшафт Бали, индустриальное наследие, археологические объекты и национальные парки. Эти места принадлежат разным эпохам и территориям, поэтому исторический контекст следует читать адресно.",
    "cuisine": "Кулинарные традиции различаются между островами и регионами. При знакомстве с блюдом полезно уточнять его происхождение, состав и локальный способ подачи у самого заведения или организатора.",
    "traditions": "Гамелан — традиционный индонезийский ударный оркестр и набор инструментов, внесённый ЮНЕСКО в Репрезентативный список. Его музыка звучит в ритуалах, церемониях, театре, фестивалях и концертах, а навыки передаются через семьи, школы и другие образовательные практики.",
    "practical": [
        {"label": "Валюта", "value": "Индонезийская рупия (IDR)"},
        {"label": "Экстренная помощь", "value": "112 · единый экстренный колл-центр; доступность уточняйте по месту"},
    ],
}

SOURCES = [
    {"label": "ЮНЕСКО: объекты Всемирного наследия Индонезии", "url": "https://whc.unesco.org/en/statesparties/ID/"},
    {"label": "ЮНЕСКО: гамелан", "url": "https://ich.unesco.org/en/RL/gamelan-01607"},
    {"label": "Банк Индонезии: управление рупией", "url": "https://www.bi.go.id/en/fungsi-utama/sistem-pembayaran/pengelolaan-rupiah/default.aspx"},
    {"label": "Indonesia.go.id: экстренная служба 112", "url": "https://indonesia.go.id/layanan/kependudukan/sosial/layanan-darurat-112?lang=1"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-id", "published_version_id": None,
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
        "status": "published", "title": "Индонезия", "body": BODY, "sources": SOURCES,
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
