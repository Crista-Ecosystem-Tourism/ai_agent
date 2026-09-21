"""add Moscow matching sandbox drill

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    content = sa.table(
        "game_content_revision",
        sa.column("id", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("payload", postgresql.JSONB()),
        sa.column("is_published", sa.Boolean()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(content, [{
        "id": "moscow-sandbox-activities-v2",
        "kind": "sandbox-activities",
        "payload": {
            "id": "moscow-sandbox-activities-v2",
            "truth_myth": {
                "title": "Правда или миф",
                "intro": "Свайпни влево для мифа или вправо для правды. Кнопки ниже работают так же и доступны с клавиатуры.",
                "statements": [
                    {
                        "id": "zaryadye-2017", "text": "Парк «Зарядье» открылся в 2017 году.",
                        "correct_answer": "truth",
                        "explanation": "Верно: ландшафтный парк у стен Кремля открылся в 2017 году.",
                        "source_label": "Комплекс градостроительной политики Москвы",
                        "source_url": "https://stroi.mos.ru/park-zariad-ie",
                    },
                    {
                        "id": "metro-1954", "text": "Первая очередь Московского метро открылась в 1954 году.",
                        "correct_answer": "myth",
                        "explanation": "Миф: первая очередь Московского метрополитена открылась 15 мая 1935 года.",
                        "source_label": "Московский метрополитен",
                        "source_url": "https://mosmetro.ru/about/history",
                    },
                    {
                        "id": "gum-1893", "text": "Верхние торговые ряды, будущий ГУМ, открылись в 1893 году.",
                        "correct_answer": "truth",
                        "explanation": "Верно: Верхние торговые ряды открылись 2 декабря 1893 года.",
                        "source_label": "ГУМ",
                        "source_url": "https://gum.ru/history/",
                    },
                ],
            },
            "matching": {
                "title": "Соедини эпохи",
                "intro": "Для каждой достопримечательности выбери связанный с ней год. Проверка и объяснения остаются на сервере.",
                "pairs": [
                    {
                        "id": "cathedral-year", "left": "Благовещенский собор",
                        "correct_choice_id": "year-1489",
                        "explanation": "Благовещенский собор Московского Кремля освятили в 1489 году.",
                    },
                    {
                        "id": "gum-year", "left": "Верхние торговые ряды",
                        "correct_choice_id": "year-1893",
                        "explanation": "Верхние торговые ряды, будущий ГУМ, открылись в 1893 году.",
                    },
                    {
                        "id": "vdnh-year", "left": "Первая выставка ВДНХ",
                        "correct_choice_id": "year-1939",
                        "explanation": "Первая Всесоюзная сельскохозяйственная выставка на территории ВДНХ открылась в 1939 году.",
                    },
                ],
                "choices": [
                    {"id": "year-1489", "label": "1489"},
                    {"id": "year-1893", "label": "1893"},
                    {"id": "year-1939", "label": "1939"},
                ],
            },
        },
        "is_published": True,
        "published_at": now,
        "created_at": now,
        "updated_at": now,
    }])
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-sandbox-activities-v2'
        WHERE id = 'moscow'
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-sandbox-activities-v2'"))
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-truth-myth-v1'
        WHERE id = 'moscow'
    """))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v2'"))
