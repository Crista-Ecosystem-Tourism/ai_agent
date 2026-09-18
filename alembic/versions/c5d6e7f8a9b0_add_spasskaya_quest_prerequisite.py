"""add Spasskaya Tower lesson and quest prerequisite

Revision ID: c5d6e7f8a9b0
Revises: b4e8a1d2c3f6
Create Date: 2026-09-18
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4e8a1d2c3f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_quest",
        sa.Column("prerequisite_quest_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_game_quest_prerequisite", "game_quest", "game_quest",
        ["prerequisite_quest_id"], ["id"],
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
    quest = sa.table(
        "game_quest",
        sa.column("id", sa.String()),
        sa.column("city_id", sa.String()),
        sa.column("content_revision_id", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("position", sa.Integer()),
        sa.column("prerequisite_quest_id", sa.String()),
        sa.column("is_published", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(content, [{
        "id": "moscow-spasskaya-v1",
        "kind": "fact-quiz",
        "payload": {
            "id": "moscow-spasskaya-v1",
            "country": {"id": "ru", "name": "Россия", "city": "Москва"},
            "chris": {
                "name": "Крис",
                "intro": "Красная площадь пройдена — теперь поднимем взгляд на главные ворота Кремля.",
            },
            "scene": {"title": "Спасская башня", "mode": "spasskaya-tower"},
            "fact": {
                "text": "Спасскую башню Московского Кремля возвёл архитектор Пьетро Антонио Солари в 1491 году.",
                "source_label": "Музеи Московского Кремля",
                "source_url": "https://kremlin-architectural-ensemble.kreml.ru/architecture/view/spasskaya-bashnya-moskovskogo-kremlya/",
            },
            "question": {
                "id": "spasskaya-year",
                "text": "В каком году была возведена Спасская башня?",
                "options": [
                    {"id": "1491", "label": "1491"},
                    {"id": "1547", "label": "1547"},
                    {"id": "1812", "label": "1812"},
                ],
                "correct_option_id": "1491",
            },
            "reward": {
                "xp": 25,
                "stamp_key": "moscow-spasskaya",
                "stamp_title": "Штамп «Спасская башня»",
            },
        },
        "is_published": True,
        "published_at": now,
        "created_at": now,
        "updated_at": now,
    }])
    op.bulk_insert(quest, [{
        "id": "moscow-spasskaya-tower",
        "city_id": "moscow",
        "content_revision_id": "moscow-spasskaya-v1",
        "kind": "fact-quiz",
        "position": 2,
        "prerequisite_quest_id": "moscow-red-square",
        "is_published": True,
        "created_at": now,
        "updated_at": now,
    }])


def downgrade() -> None:
    op.execute(sa.text(
        "DELETE FROM game_quest_completion WHERE quest_id = 'moscow-spasskaya-tower'"
    ))
    op.execute(sa.text(
        "DELETE FROM game_stamp WHERE content_revision_id = 'moscow-spasskaya-v1'"
    ))
    op.execute(sa.text(
        "DELETE FROM game_attempt WHERE content_revision_id = 'moscow-spasskaya-v1'"
    ))
    op.execute(sa.text("DELETE FROM game_quest WHERE id = 'moscow-spasskaya-tower'"))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-spasskaya-v1'"))
    op.drop_constraint("fk_game_quest_prerequisite", "game_quest", type_="foreignkey")
    op.drop_column("game_quest", "prerequisite_quest_id")
