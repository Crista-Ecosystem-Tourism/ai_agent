"""add Moscow daily progress, reward ledger and third quest

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-18
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_profile",
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("game_profile", sa.Column("last_activity_on", sa.Date(), nullable=True))
    op.create_table(
        "game_daily_progress",
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), primary_key=True),
        sa.Column("goal_date", sa.Date(), primary_key=True),
        sa.Column("completed_quests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goal_reached_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "game_reward_ledger",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("quest_id", sa.String(), sa.ForeignKey("game_quest.id"), nullable=False),
        sa.Column("reward_key", sa.String(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "reward_key", name="uq_game_reward_user_key"),
    )
    op.create_index("idx_game_reward_user_awarded", "game_reward_ledger", ["user_id", "awarded_at"])

    # Preserve the audit trail for users who received the two earlier stamps.
    op.execute(sa.text("""
        INSERT INTO game_reward_ledger (id, user_id, quest_id, reward_key, xp, awarded_at)
        SELECT
          md5(s.user_id || ':' || s.stamp_key),
          s.user_id,
          CASE s.stamp_key
            WHEN 'moscow-starter' THEN 'moscow-red-square'
            WHEN 'moscow-spasskaya' THEN 'moscow-spasskaya-tower'
          END,
          s.stamp_key,
          CASE s.stamp_key
            WHEN 'moscow-starter' THEN 50
            WHEN 'moscow-spasskaya' THEN 25
          END,
          s.earned_at
        FROM game_stamp s
        WHERE s.stamp_key IN ('moscow-starter', 'moscow-spasskaya')
        ON CONFLICT ON CONSTRAINT uq_game_reward_user_key DO NOTHING
    """))

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
        "id": "moscow-tsar-bell-v1",
        "kind": "fact-quiz",
        "payload": {
            "id": "moscow-tsar-bell-v1",
            "country": {"id": "ru", "name": "Россия", "city": "Москва"},
            "chris": {
                "name": "Крис",
                "intro": "За Спасской башней начинается Кремль — здесь хранится история самого большого колокола в мире.",
            },
            "scene": {"title": "Царь-колокол", "mode": "tsar-bell"},
            "fact": {
                "text": "Царь-колокол отлили по указу Анны Иоанновны в 1735 году; это самый большой колокол в мире, но он никогда не звонил.",
                "source_label": "Музеи Московского Кремля",
                "source_url": "https://kremlin-architectural-ensemble.kreml.ru/the-tsar-bell/view/",
            },
            "question": {
                "id": "tsar-bell-year",
                "text": "В каком году было завершено литьё Царь-колокола?",
                "options": [
                    {"id": "1613", "label": "1613"},
                    {"id": "1735", "label": "1735"},
                    {"id": "1836", "label": "1836"},
                ],
                "correct_option_id": "1735",
            },
            "reward": {
                "xp": 25,
                "stamp_key": "moscow-tsar-bell",
                "stamp_title": "Штамп «Царь-колокол»",
            },
        },
        "is_published": True,
        "published_at": now,
        "created_at": now,
        "updated_at": now,
    }])
    op.bulk_insert(quest, [{
        "id": "moscow-tsar-bell",
        "city_id": "moscow",
        "content_revision_id": "moscow-tsar-bell-v1",
        "kind": "fact-quiz",
        "position": 3,
        "prerequisite_quest_id": "moscow-spasskaya-tower",
        "is_published": True,
        "created_at": now,
        "updated_at": now,
    }])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_quest_completion WHERE quest_id = 'moscow-tsar-bell'"))
    op.execute(sa.text("DELETE FROM game_stamp WHERE content_revision_id = 'moscow-tsar-bell-v1'"))
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-tsar-bell-v1'"))
    op.execute(sa.text("DELETE FROM game_reward_ledger WHERE reward_key = 'moscow-tsar-bell'"))
    op.execute(sa.text("DELETE FROM game_quest WHERE id = 'moscow-tsar-bell'"))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-tsar-bell-v1'"))
    op.drop_index("idx_game_reward_user_awarded", table_name="game_reward_ledger")
    op.drop_table("game_reward_ledger")
    op.drop_table("game_daily_progress")
    op.drop_column("game_profile", "last_activity_on")
    op.drop_column("game_profile", "streak")
