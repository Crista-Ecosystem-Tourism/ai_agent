"""publish the first country catalogue Wiki version for Japan

Revision ID: t9b0c1d2e3f4
Revises: s8a9b0c1d2e3
Create Date: 2026-09-24
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "t9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "s8a9b0c1d2e3"
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
        "id": "wiki-country-jp", "slug": "country-jp", "published_version_id": None,
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
        "id": "wiki-country-jp-v1", "article_id": "wiki-country-jp", "author_id": "crista-editorial",
        "status": "published", "title": "Япония", "license": "CC BY 4.0",
        "body": {
            "summary": "Япония — страна с разнообразными региональными культурами; знакомство с её историей и повседневными обычаями помогает читать места внимательнее.",
            "history": "В период Эдо (1603–1867) развивалась городская культура, включая кабуки и гравюру укиё-э. Реставрация Мэйдзи началась в 1868 году и сопровождалась масштабной модернизацией страны.",
            "cuisine": "Washoku — традиционная японская культура питания — включена в список нематериального культурного наследия ЮНЕСКО в 2013 году. В ней подчёркиваются сезонность, разнообразие местных продуктов и региональные различия.",
            "traditions": "Обычаи различаются по регионам и ситуациям. В гостях и некоторых заведениях перед входом могут попросить снять обувь; за столом полезно сначала посмотреть, как устроена подача конкретного блюда.",
            "practical": [
                {"label": "Валюта", "value": "Японская иена (JPY, ¥)"},
                {"label": "Полиция · срочно", "value": "110"},
                {"label": "Пожарная служба / скорая · срочно", "value": "119"},
            ],
        },
        "sources": [
            {"label": "JNTO: обзор истории Японии", "url": "https://www.japan.travel/en/responsible-travel-guide/features/overview-japanese-history/"},
            {"label": "MAFF: что такое washoku", "url": "https://www.maff.go.jp/e/policies/market/washoku-world-challenge/en/learning_01.html"},
            {"label": "JNTO: валюта и обмен", "url": "https://www.japan.travel/en/plan/currency/"},
            {"label": "JNTO: экстренные номера", "url": "https://www.japan.travel/en/plan/hotline/"},
        ],
        "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    }])
    op.execute(sa.text("UPDATE wiki_article SET published_version_id = 'wiki-country-jp-v1' WHERE id = 'wiki-country-jp'"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM wiki_article_version WHERE id = 'wiki-country-jp-v1'"))
    op.execute(sa.text("DELETE FROM wiki_article WHERE id = 'wiki-country-jp'"))
