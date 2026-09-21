"""add Moscow word-blocks sandbox drill

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.execute(sa.text("""
        INSERT INTO game_content_revision (
            id, kind, payload, is_published, published_at, created_at, updated_at
        )
        SELECT
            'moscow-sandbox-activities-v4',
            'sandbox-activities',
            payload || CAST('{
              "id": "moscow-sandbox-activities-v4",
              "word_blocks": {
                "title": "Собери фразу",
                "intro": "Поставь слова в естественном порядке кнопками «выше» и «ниже», затем проверь фразу.",
                "blocks": [
                  {"id": "word-capital", "label": "столица"},
                  {"id": "word-russia", "label": "России"},
                  {"id": "word-moscow", "label": "Москва"},
                  {"id": "word-dash", "label": "—"}
                ],
                "expected_order": ["word-moscow", "word-dash", "word-capital", "word-russia"],
                "explanation": "Верно: «Москва — столица России»."
              }
            }' AS jsonb),
            TRUE,
            :now,
            :now,
            :now
        FROM game_content_revision
        WHERE id = 'moscow-sandbox-activities-v3'
    """).bindparams(now=now))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v4'
        WHERE id = 'moscow'
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-sandbox-activities-v4'"))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v3'
        WHERE id = 'moscow'
    """))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v4'"))
