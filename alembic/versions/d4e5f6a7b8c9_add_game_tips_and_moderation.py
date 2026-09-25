"""Add location tips, reports, and an append-only moderation journal."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_tip",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("quest_id", sa.String(), nullable=False),
        sa.Column("author_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_id", sa.String(), nullable=True),
        sa.Column("decision_note", sa.String(length=500), nullable=True),
        sa.CheckConstraint("status IN ('draft', 'review', 'published', 'rejected', 'hidden')", name="game_tip_status"),
        sa.CheckConstraint("length(body) BETWEEN 10 AND 1200", name="game_tip_body_length"),
        sa.ForeignKeyConstraint(["quest_id"], ["game_quest.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["author_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_game_tip_quest_status", "game_tip", ["quest_id", "status", "created_at"])
    op.create_index("idx_game_tip_author_status_updated", "game_tip", ["author_id", "status", "updated_at"])

    op.create_table(
        "game_tip_report",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tip_id", sa.String(), nullable=False),
        sa.Column("reporter_id", sa.String(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("details", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.String(), nullable=True),
        sa.Column("resolution_note", sa.String(length=500), nullable=True),
        sa.CheckConstraint("reason IN ('inaccurate', 'unsafe', 'spam', 'copyright', 'other')", name="game_tip_report_reason"),
        sa.CheckConstraint("status IN ('pending', 'resolved', 'dismissed')", name="game_tip_report_status"),
        sa.ForeignKeyConstraint(["tip_id"], ["game_tip.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tip_id", "reporter_id", name="uq_game_tip_reporter_once"),
    )
    op.create_index("idx_game_tip_report_status", "game_tip_report", ["status", "created_at"])

    op.create_table(
        "game_tip_moderation_action",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tip_id", sa.String(), nullable=True),
        sa.Column("report_id", sa.String(), nullable=True),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tip_id"], ["game_tip.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_id"], ["game_tip_report.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_game_tip_action_created", "game_tip_moderation_action", ["created_at"])
    op.create_index("idx_game_tip_action_tip", "game_tip_moderation_action", ["tip_id", "created_at"])
    op.create_index("idx_game_tip_action_actor_window", "game_tip_moderation_action", ["actor_id", "action", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_game_tip_action_actor_window", table_name="game_tip_moderation_action")
    op.drop_index("idx_game_tip_action_tip", table_name="game_tip_moderation_action")
    op.drop_index("idx_game_tip_action_created", table_name="game_tip_moderation_action")
    op.drop_table("game_tip_moderation_action")
    op.drop_index("idx_game_tip_report_status", table_name="game_tip_report")
    op.drop_table("game_tip_report")
    op.drop_index("idx_game_tip_author_status_updated", table_name="game_tip")
    op.drop_index("idx_game_tip_quest_status", table_name="game_tip")
    op.drop_table("game_tip")
