"""Add team quest snapshots with individually deduplicated rewards."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_team_quest",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("quest_id", sa.String(), nullable=False),
        sa.Column("created_by_id", sa.String(), nullable=False),
        sa.Column("reward_xp", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("reward_xp >= 1", name="social_team_quest_positive_xp"),
        sa.CheckConstraint("status IN ('active', 'complete')", name="social_team_quest_status"),
        sa.ForeignKeyConstraint(["team_id"], ["social_team.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quest_id"], ["game_quest.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "quest_id", name="uq_social_team_quest_once"),
    )
    op.create_index("idx_social_team_quest_status", "social_team_quest", ["team_id", "status"])

    op.create_table(
        "social_team_quest_participant",
        sa.Column("team_quest_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_quest_id"], ["social_team_quest.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("team_quest_id", "user_id"),
    )
    op.create_index("idx_social_team_quest_participant_user", "social_team_quest_participant", ["user_id", "team_quest_id"])


def downgrade() -> None:
    op.drop_index("idx_social_team_quest_participant_user", table_name="social_team_quest_participant")
    op.drop_table("social_team_quest_participant")
    op.drop_index("idx_social_team_quest_status", table_name="social_team_quest")
    op.drop_table("social_team_quest")
