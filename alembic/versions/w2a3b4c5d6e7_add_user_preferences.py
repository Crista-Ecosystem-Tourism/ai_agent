"""Persist user interface preferences on the account."""
from alembic import op
import sqlalchemy as sa


revision = "w2a3b4c5d6e7"
down_revision = "v1d2e3f4a5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_user", sa.Column("preferred_theme", sa.String(), nullable=False, server_default="dark"))
    op.add_column("app_user", sa.Column("preferred_language", sa.String(), nullable=False, server_default="ru"))
    op.alter_column("app_user", "preferred_theme", server_default=None)
    op.alter_column("app_user", "preferred_language", server_default=None)


def downgrade() -> None:
    op.drop_column("app_user", "preferred_language")
    op.drop_column("app_user", "preferred_theme")
