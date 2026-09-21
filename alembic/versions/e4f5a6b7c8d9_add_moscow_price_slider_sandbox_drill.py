"""add Moscow price-slider sandbox drill

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.execute(sa.text("""
        INSERT INTO game_content_revision (
            id, kind, payload, is_published, published_at, created_at, updated_at
        )
        SELECT
            'moscow-sandbox-activities-v5',
            'sandbox-activities',
            payload || CAST('{
              "id": "moscow-sandbox-activities-v5",
              "price_slider": {
                "title": "Угадай цену",
                "intro": "Передвинь ползунок и оцени историческую стоимость. Допуск и точный ответ проверяются только сервером.",
                "question": "Сколько стоил билет на первую очередь Московского метро в день открытия?",
                "fact_date": "15 мая 1935 года",
                "unit": "коп.",
                "min": 0,
                "max": 100,
                "step": 5,
                "target": 50,
                "tolerance": 10,
                "explanation": "В день открытия первой очереди Московского метро, 15 мая 1935 года, проезд стоил 50 копеек.",
                "source_label": "Московский метрополитен",
                "source_url": "https://mosmetro.ru/about/history"
              }
            }' AS jsonb),
            TRUE,
            :now,
            :now,
            :now
        FROM game_content_revision
        WHERE id = 'moscow-sandbox-activities-v4'
    """).bindparams(now=now))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v5'
        WHERE id = 'moscow'
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-sandbox-activities-v5'"))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v4'
        WHERE id = 'moscow'
    """))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v5'"))
