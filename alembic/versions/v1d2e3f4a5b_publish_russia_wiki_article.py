"""publish the Russia country catalogue Wiki version

Revision ID: v1d2e3f4a5b
Revises: u0c1d2e3f4a
Create Date: 2026-09-24
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v1d2e3f4a5b"
down_revision: Union[str, Sequence[str], None] = "u0c1d2e3f4a"
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
        "id": "wiki-country-ru", "slug": "country-ru", "published_version_id": None,
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
        "id": "wiki-country-ru-v1", "article_id": "wiki-country-ru", "author_id": "crista-editorial",
        "status": "published", "title": "Россия", "license": "CC BY 4.0",
        "body": {
            "summary": "Россия объединяет множество регионов и народов, поэтому её культурные традиции и повседневная кухня заметно различаются от места к месту.",
            "history": "Историю Москвы можно проследить по ансамблю Кремля: первое письменное упоминание города относится к 1147 году, а кирпичные стены и башни Кремля в основном относятся к перестройке 1485–1495 годов.",
            "cuisine": "У кухни разных регионов свои продукты и рецепты. В центральной России распространены щи, каши и выпечка; в Поволжье местные традиции разных народов повлияли на блюда региона, а южная кухня использует собственные овощи и приправы.",
            "traditions": "В России живут народы с разными языками, ремёслами, праздниками и обычаями. Региональный контекст важен: одна традиция или блюдо не описывает всю страну.",
            "practical": [
                {"label": "Валюта", "value": "Российский рубль (₽)"},
                {"label": "Единый номер экстренных служб", "value": "112"},
            ],
        },
        "sources": [
            {"label": "Музеи Московского Кремля: история ансамбля", "url": "https://kremlin-architectural-ensemble.kreml.ru/en-Us/history/view/"},
            {"label": "Культура.РФ: региональные кухни России", "url": "https://www.culture.ru/materials/254771/kukhni-rossii-tradicionnye-blyuda-i-ikh-istoriya"},
            {"label": "Культура.РФ: народы России", "url": "https://www.culture.ru/s/narody-rossii/"},
            {"label": "Банк России: наличное денежное обращение", "url": "https://www.cbr.ru/eng/cash_circulation/"},
            {"label": "МЧС России: вызов экстренных служб", "url": "https://mchs.gov.ru/deyatelnost/bezopasnost-grazhdan/kak-pravilno-vyzvat-skoruyu_5"},
        ],
        "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    }])
    op.execute(sa.text("UPDATE wiki_article SET published_version_id = 'wiki-country-ru-v1' WHERE id = 'wiki-country-ru'"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM wiki_article_version WHERE id = 'wiki-country-ru-v1'"))
    op.execute(sa.text("DELETE FROM wiki_article WHERE id = 'wiki-country-ru'"))
