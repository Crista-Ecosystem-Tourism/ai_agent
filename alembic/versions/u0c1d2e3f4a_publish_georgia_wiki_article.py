"""publish the Georgia country catalogue Wiki version

Revision ID: u0c1d2e3f4a
Revises: t9b0c1d2e3f4
Create Date: 2026-09-24
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "u0c1d2e3f4a"
down_revision: Union[str, Sequence[str], None] = "t9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": "wiki-country-ge", "slug": "country-ge", "published_version_id": None,
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
        "id": "wiki-country-ge-v1", "article_id": "wiki-country-ge", "author_id": "crista-editorial",
        "status": "published", "title": "Грузия", "license": "CC BY 4.0",
        "body": {
            "summary": "Грузия — страна Кавказа с разнообразными региональными кухнями и живыми традициями, в которых важную роль играют местные сообщества.",
            "history": "На территории современной восточной Грузии в IV веке до нашей эры развивалось царство Иберия. В начале XI века несколько грузинских государств объединились; история страны складывалась на пересечении региональных культур и политических влияний.",
            "cuisine": "Грузинская кухня заметно различается по регионам. Среди широко известных блюд — хинкали и хачапури; у хачапури есть региональные варианты. Традиционный способ изготовления вина в квеври включён ЮНЕСКО в Репрезентативный список нематериального культурного наследия человечества.",
            "traditions": "Застольные обычаи и рецепты отличаются от региона к региону. Традиция виноделия в квеври поддерживается семьями и общинами: знания о глиняных сосудах и процессе передаются между поколениями.",
            "practical": [
                {"label": "Валюта", "value": "Грузинский лари (GEL)"},
                {"label": "Экстренный номер", "value": "112 · полиция, пожарная служба и скорая помощь"},
            ],
        },
        "sources": [
            {"label": "Georgia Travel: история Грузии", "url": "https://georgia.travel/why-georgia-history"},
            {"label": "Georgia Travel: кухня Грузии", "url": "https://georgia.travel/georgian-cuisine"},
            {"label": "ЮНЕСКО: традиционный способ виноделия в квеври", "url": "https://ich.unesco.org/en/decisions/8.COM/8.13"},
            {"label": "Georgia Travel: валюта", "url": "https://georgia.travel/coming-to-georgia/currency"},
            {"label": "112 Georgia: когда звонить", "url": "https://112.gov.ge/?lang=en&page_id=1686"},
        ],
        "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    }])
    op.execute(sa.text("UPDATE wiki_article SET published_version_id = 'wiki-country-ge-v1' WHERE id = 'wiki-country-ge'"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM wiki_article_version WHERE id = 'wiki-country-ge-v1'"))
    op.execute(sa.text("DELETE FROM wiki_article WHERE id = 'wiki-country-ge'"))
