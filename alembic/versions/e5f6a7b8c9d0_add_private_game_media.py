"""Add owner-scoped, quest-linked private image assets."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_media_asset",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("quest_id", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("preview_key", sa.String(length=80), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("content_type = 'image/jpeg'", name="game_media_jpeg_only"),
        sa.CheckConstraint("byte_size BETWEEN 1 AND 10485760", name="game_media_size_limit"),
        sa.CheckConstraint("width > 0 AND height > 0", name="game_media_dimensions_positive"),
        sa.ForeignKeyConstraint(["owner_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quest_id"], ["game_quest.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_game_media_asset_storage_key"),
        sa.UniqueConstraint("preview_key", name="uq_game_media_asset_preview_key"),
    )
    op.create_index("idx_game_media_owner_created", "game_media_asset", ["owner_id", "created_at"])
    op.create_index("idx_game_media_quest_created", "game_media_asset", ["quest_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_game_media_quest_created", table_name="game_media_asset")
    op.drop_index("idx_game_media_owner_created", table_name="game_media_asset")
    op.drop_table("game_media_asset")
