"""Allow validated short videos in the private quest media library."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("game_media_jpeg_only", "game_media_asset", type_="check")
    op.drop_constraint("game_media_size_limit", "game_media_asset", type_="check")
    op.add_column("game_media_asset", sa.Column("duration_seconds", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "game_media_type_allowed", "game_media_asset",
        "content_type IN ('image/jpeg', 'video/mp4', 'video/webm')",
    )
    op.create_check_constraint(
        "game_media_size_limit", "game_media_asset", "byte_size BETWEEN 1 AND 52428800",
    )
    op.create_check_constraint(
        "game_media_duration_limit", "game_media_asset",
        "duration_seconds IS NULL OR duration_seconds BETWEEN 1 AND 60",
    )


def downgrade() -> None:
    op.drop_constraint("game_media_duration_limit", "game_media_asset", type_="check")
    op.drop_constraint("game_media_size_limit", "game_media_asset", type_="check")
    op.drop_constraint("game_media_type_allowed", "game_media_asset", type_="check")
    op.drop_column("game_media_asset", "duration_seconds")
    op.create_check_constraint("game_media_size_limit", "game_media_asset", "byte_size BETWEEN 1 AND 10485760")
    op.create_check_constraint("game_media_jpeg_only", "game_media_asset", "content_type = 'image/jpeg'")
