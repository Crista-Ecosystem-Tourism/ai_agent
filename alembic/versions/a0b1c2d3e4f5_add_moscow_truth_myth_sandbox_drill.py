"""add Moscow truth-or-myth sandbox drill

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "f9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_city", sa.Column("sandbox_content_revision_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_game_city_sandbox_content", "game_city", "game_content_revision",
        ["sandbox_content_revision_id"], ["id"],
    )
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
        "id": "moscow-truth-myth-v1",
        "kind": "truth-myth",
        "payload": {
            "id": "moscow-truth-myth-v1",
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
        "is_published": True,
        "published_at": now,
        "created_at": now,
        "updated_at": now,
    }])
    op.execute(sa.text("""
        UPDATE game_city
        SET sandbox_content_revision_id = 'moscow-truth-myth-v1'
        WHERE id = 'moscow'
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-truth-myth-v1'"))
    op.execute(sa.text("UPDATE game_city SET sandbox_content_revision_id = NULL WHERE id = 'moscow'"))
    op.drop_constraint("fk_game_city_sandbox_content", "game_city", type_="foreignkey")
    op.drop_column("game_city", "sandbox_content_revision_id")
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-truth-myth-v1'"))
