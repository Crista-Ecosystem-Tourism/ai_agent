"""Add weekly league seasons and rank snapshots; merge current migration heads."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = (
    "e6f7a8b9c0d1",
    "s8a9b0c1d2e3",
    "z7f8a9b0c1d",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "league_season",
        sa.Column("id", sa.String(length=8), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("ends_at > starts_at", name="league_season_positive_window"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="league_season_status"),
        sa.CheckConstraint(
            "(status = 'open' AND closed_at IS NULL) OR (status = 'closed' AND closed_at IS NOT NULL)",
            name="league_season_closed_at_matches_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_league_season_status_ends", "league_season", ["status", "ends_at"])

    op.create_table(
        "league_membership",
        sa.Column("season_id", sa.String(length=8), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weekly_xp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("final_place", sa.Integer(), nullable=True),
        sa.Column("final_rank", sa.Integer(), nullable=True),
        sa.Column("movement", sa.String(length=12), nullable=True),
        sa.CheckConstraint("rank BETWEEN 1 AND 10", name="league_membership_rank_range"),
        sa.CheckConstraint("weekly_xp >= 0", name="league_membership_nonnegative_xp"),
        sa.CheckConstraint("final_rank IS NULL OR final_rank BETWEEN 1 AND 10", name="league_membership_final_rank_range"),
        sa.CheckConstraint("final_place IS NULL OR final_place >= 1", name="league_membership_final_place_positive"),
        sa.CheckConstraint(
            "movement IS NULL OR movement IN ('promoted', 'held', 'relegated')",
            name="league_membership_movement",
        ),
        sa.ForeignKeyConstraint(["season_id"], ["league_season.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("season_id", "user_id"),
    )
    op.create_index("idx_league_membership_user_joined", "league_membership", ["user_id", "joined_at"])


def downgrade() -> None:
    op.drop_index("idx_league_membership_user_joined", table_name="league_membership")
    op.drop_table("league_membership")
    op.drop_index("idx_league_season_status_ends", table_name="league_season")
    op.drop_table("league_season")
