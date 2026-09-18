"""add the Moscow city boss and completion stamp

Revision ID: f9a0b1c2d3e4
Revises: e7f8a9b0c1d2
Create Date: 2026-09-18
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_city",
        sa.Column("boss_content_revision_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_game_city_boss_content", "game_city", "game_content_revision",
        ["boss_content_revision_id"], ["id"],
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
        "id": "moscow-city-boss-v1",
        "kind": "city-boss",
        "payload": {
            "id": "moscow-city-boss-v1",
            "chris": {
                "name": "Крис",
                "intro": "Ты прошёл весь городской круг. Собери три факта в одну историю Москвы — и получи городской штамп.",
            },
            "scene": {"title": "Финальный круг Москвы", "mode": "city-boss"},
            "questions": [
                {
                    "id": "moscow-boss-cathedral", "text": "В каком году освятили Благовещенский собор?",
                    "options": [{"id": "1489", "label": "1489"}, {"id": "1561", "label": "1561"}, {"id": "1613", "label": "1613"}],
                    "correct_option_id": "1489",
                    "explanation": "Собор построили в 1484–1489 годах и освятили в 1489 году.",
                },
                {
                    "id": "moscow-boss-gum", "text": "В каком году открылись Верхние торговые ряды, будущий ГУМ?",
                    "options": [{"id": "1825", "label": "1825"}, {"id": "1893", "label": "1893"}, {"id": "1939", "label": "1939"}],
                    "correct_option_id": "1893",
                    "explanation": "Верхние торговые ряды открылись 2 декабря 1893 года.",
                },
                {
                    "id": "moscow-boss-vdnh", "text": "В каком году открылась первая выставка на территории ВДНХ?",
                    "options": [{"id": "1923", "label": "1923"}, {"id": "1939", "label": "1939"}, {"id": "1959", "label": "1959"}],
                    "correct_option_id": "1939",
                    "explanation": "История ВДНХ началась с выставки, открывшейся 1 августа 1939 года.",
                },
            ],
            "sources": [
                {"label": "Музеи Московского Кремля", "url": "https://annunciation-cathedral.kreml.ru/history/view/"},
                {"label": "ГУМ", "url": "https://gum.ru/history/"},
                {"label": "ВДНХ", "url": "https://vdnh.ru/visitors/about/"},
            ],
        },
        "is_published": True,
        "published_at": now,
        "created_at": now,
        "updated_at": now,
    }])
    op.execute(sa.text("""
        UPDATE game_city
        SET boss_content_revision_id = 'moscow-city-boss-v1'
        WHERE id = 'moscow'
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_stamp WHERE content_revision_id = 'moscow-city-boss-v1'"))
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-city-boss-v1'"))
    op.execute(sa.text("UPDATE game_city SET boss_content_revision_id = NULL WHERE id = 'moscow'"))
    op.drop_constraint("fk_game_city_boss_content", "game_city", type_="foreignkey")
    op.drop_column("game_city", "boss_content_revision_id")
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-city-boss-v1'"))
