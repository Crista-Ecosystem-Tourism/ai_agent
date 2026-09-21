"""add Moscow timeline sandbox drill

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.execute(sa.text("""
        INSERT INTO game_content_revision (
            id, kind, payload, is_published, published_at, created_at, updated_at
        )
        SELECT
            'moscow-sandbox-activities-v3',
            'sandbox-activities',
            payload || CAST('{
              "id": "moscow-sandbox-activities-v3",
              "timeline": {
                "title": "Собери хронологию",
                "intro": "Поставь события от самого раннего к позднему кнопками «выше» и «ниже», затем проверь порядок.",
                "items": [
                  {
                    "id": "metro-1935",
                    "label": "Открылась первая очередь Московского метро",
                    "correct_position": 2,
                    "explanation": "Первая очередь Московского метрополитена открылась 15 мая 1935 года."
                  },
                  {
                    "id": "gum-1893",
                    "label": "Открылись Верхние торговые ряды",
                    "correct_position": 1,
                    "explanation": "Верхние торговые ряды, будущий ГУМ, открылись 2 декабря 1893 года."
                  },
                  {
                    "id": "vdnh-1939",
                    "label": "Открылась первая выставка на территории ВДНХ",
                    "correct_position": 3,
                    "explanation": "Первая Всесоюзная сельскохозяйственная выставка на территории ВДНХ открылась в 1939 году."
                  }
                ]
              }
            }' AS jsonb),
            TRUE,
            :now,
            :now,
            :now
        FROM game_content_revision
        WHERE id = 'moscow-sandbox-activities-v2'
    """).bindparams(now=now))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v3'
        WHERE id = 'moscow'
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-sandbox-activities-v3'"))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v2'
        WHERE id = 'moscow'
    """))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v3'"))
