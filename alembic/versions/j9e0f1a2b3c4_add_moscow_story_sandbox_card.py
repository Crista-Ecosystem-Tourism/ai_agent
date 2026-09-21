"""add Moscow Story sandbox card

Revision ID: j9e0f1a2b3c4
Revises: i8d9e0f1a2b3
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "i8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.execute(sa.text("""
        INSERT INTO game_content_revision (
            id, kind, payload, is_published, published_at, created_at, updated_at
        )
        SELECT
            'moscow-sandbox-activities-v6',
            'sandbox-activities',
            payload || CAST('{
              "id": "moscow-sandbox-activities-v6",
              "story": {
                "title": "Сцена: Красная площадь",
                "eyebrow": "Story · 1 из 1",
                "image_url": "/images/story/moscow-red-square-illustration-v1.png",
                "image_alt": "Стилизованная иллюстрация Красной площади, храма Василия Блаженного и кремлёвской стены в вечернем свете",
                "media_credit": "Оригинальная иллюстрация Crista, созданная для учебной Story-карты",
                "fact": "Название площади не связано с цветом: в старину слово «красный» означало «красивый».",
                "source_label": "Правительство Москвы · «Москва: что посмотреть»",
                "source_url": "https://www.mos.ru/upload/documents/files/2937/Moskvachtoposmotret.pdf",
                "note": "Иллюстрация помогает представить сцену, но исторический факт проверяется по первоисточнику."
              }
            }' AS jsonb),
            TRUE,
            :now,
            :now,
            :now
        FROM game_content_revision
        WHERE id = 'moscow-sandbox-activities-v5'
    """).bindparams(now=now))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v6'
        WHERE id = 'moscow'
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-sandbox-activities-v6'"))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v5'
        WHERE id = 'moscow'
    """))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v6'"))
