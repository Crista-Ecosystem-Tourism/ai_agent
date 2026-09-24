"""Add privacy-safe friend invites and symmetric accepted friendships."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "z9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "friend_invite",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("inviter_id", sa.String(), nullable=False),
        sa.Column("accepted_by_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "accepted_by_id IS NULL OR accepted_by_id <> inviter_id",
            name="friend_invite_not_self_accepted",
        ),
        sa.ForeignKeyConstraint(["inviter_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["accepted_by_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("idx_friend_invite_inviter_created", "friend_invite", ["inviter_id", "created_at"])
    op.create_index("idx_friend_invite_expires", "friend_invite", ["expires_at"])

    op.create_table(
        "friendship",
        sa.Column("user_a_id", sa.String(), nullable=False),
        sa.Column("user_b_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("user_a_id < user_b_id", name="friendship_canonical_user_order"),
        sa.ForeignKeyConstraint(["user_a_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_a_id", "user_b_id"),
    )
    op.create_index("idx_friendship_user_b", "friendship", ["user_b_id"])

    op.create_table(
        "social_team",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_by_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_social_team_creator", "social_team", ["created_by_id", "created_at"])

    op.create_table(
        "social_team_membership",
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'admin', 'member')", name="social_team_membership_role"),
        sa.ForeignKeyConstraint(["team_id"], ["social_team.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("team_id", "user_id"),
    )
    op.create_index("idx_social_team_membership_user", "social_team_membership", ["user_id", "team_id"])


def downgrade() -> None:
    op.drop_index("idx_social_team_membership_user", table_name="social_team_membership")
    op.drop_table("social_team_membership")
    op.drop_index("idx_social_team_creator", table_name="social_team")
    op.drop_table("social_team")
    op.drop_index("idx_friendship_user_b", table_name="friendship")
    op.drop_table("friendship")
    op.drop_index("idx_friend_invite_expires", table_name="friend_invite")
    op.drop_index("idx_friend_invite_inviter_created", table_name="friend_invite")
    op.drop_table("friend_invite")
