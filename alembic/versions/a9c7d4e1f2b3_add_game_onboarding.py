"""add server backed game onboarding

Revision ID: a9c7d4e1f2b3
Revises: f7a1b2c3d4e5
Create Date: 2026-09-16
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a9c7d4e1f2b3"
down_revision: Union[str, Sequence[str], None] = "f7a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_content_revision",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "game_profile",
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), primary_key=True),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("energy_refreshed_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "game_attempt",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("content_revision_id", sa.String(), sa.ForeignKey("game_content_revision.id"), nullable=False),
        sa.Column("interaction_key", sa.String(), nullable=False),
        sa.Column("answer_key", sa.String(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_game_attempt_user_created", "game_attempt", ["user_id", "created_at"])
    op.create_table(
        "game_stamp",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("stamp_key", sa.String(), nullable=False),
        sa.Column("content_revision_id", sa.String(), sa.ForeignKey("game_content_revision.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "stamp_key", name="uq_game_stamp_user_key"),
    )
    op.create_index("idx_game_stamp_user_earned", "game_stamp", ["user_id", "earned_at"])

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
        "id": "onboarding-moscow-v1",
        "kind": "onboarding",
        "payload": {
            "id": "onboarding-moscow-v1",
            "country": {"id": "ru", "name": "Россия", "city": "Москва"},
            "chris": {
                "name": "Крис",
                "intro": "Привет, я Крис! Отправимся в мини-путешествие по Москве.",
            },
            "scene": {"title": "Красная площадь", "mode": "red-square"},
            "fact": {
                "text": "Название площади не связано с цветом: в старину слово «красный» означало «красивый».",
                "source_url": "https://www.mos.ru/upload/documents/files/2937/Moskvachtoposmotret.pdf",
            },
            "question": {
                "id": "red-square-name",
                "text": "Какой смысл имело слово «красный» в старом названии площади?",
                "options": [
                    {"id": "color", "label": "Цвет"},
                    {"id": "beautiful", "label": "Красивый"},
                    {"id": "military", "label": "Военный"},
                ],
                "correct_option_id": "beautiful",
            },
            "reward": {"xp": 50, "stamp_title": "Стартовый штамп — Москва"},
        },
        "is_published": True,
        "published_at": now,
        "created_at": now,
        "updated_at": now,
    }])


def downgrade() -> None:
    op.drop_index("idx_game_stamp_user_earned", table_name="game_stamp")
    op.drop_table("game_stamp")
    op.drop_index("idx_game_attempt_user_created", table_name="game_attempt")
    op.drop_table("game_attempt")
    op.drop_table("game_profile")
    op.drop_table("game_content_revision")
