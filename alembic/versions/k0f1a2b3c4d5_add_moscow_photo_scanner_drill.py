"""add Moscow photo-scanner sandbox drill

Revision ID: k0f1a2b3c4d5
Revises: j9e0f1a2b3c4
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k0f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "j9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.execute(sa.text("""
        INSERT INTO game_content_revision (id, kind, payload, is_published, published_at, created_at, updated_at)
        SELECT
            'moscow-sandbox-activities-v7',
            'sandbox-activities',
            payload || CAST('{
              "id": "moscow-sandbox-activities-v7",
              "photo_scanner": {
                "title": "Фото-сканер: Кремлёвская стена",
                "intro": "Рассмотри настоящий снимок Красной площади и отметь область с зубцами кремлёвской стены.",
                "question": "Где на снимке видны зубцы кремлёвской стены?",
                "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Moscow%20-%20Red%20Square%2C%20the%20Kremlin%20Wall.jpg?width=1600",
                "image_alt": "Фотография кремлёвской стены на Красной площади в Москве при голубом небе",
                "media_credit": "Юрий Д.К. / Wikimedia Commons",
                "media_source_url": "https://commons.wikimedia.org/wiki/File:Moscow_-_Red_Square,_the_Kremlin_Wall.jpg",
                "license": "CC BY 4.0",
                "field_note": "Это экранное упражнение по лицензированному снимку: камера, геолокация и AR пока не подключены.",
                "hotspots": [
                  {"id": "wall-merlons", "x": 10, "y": 38, "width": 80, "height": 28},
                  {"id": "sky", "x": 18, "y": 4, "width": 58, "height": 24},
                  {"id": "foreground", "x": 20, "y": 72, "width": 58, "height": 20}
                ],
                "correct_hotspot_id": "wall-merlons",
                "explanation": "Зубцы идут по верхней линии кремлёвской стены. Сверь её с подписью и лицензией исходного снимка."
              }
            }' AS jsonb),
            TRUE, :now, :now, :now
        FROM game_content_revision
        WHERE id = 'moscow-sandbox-activities-v6'
    """).bindparams(now=now))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v7'
        WHERE id = 'moscow'
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-sandbox-activities-v7'"))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v6'
        WHERE id = 'moscow'
    """))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v7'"))
