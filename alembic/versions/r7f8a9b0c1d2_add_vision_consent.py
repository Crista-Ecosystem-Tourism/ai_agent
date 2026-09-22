"""add explicit vision consent fields

Revision ID: r7f8a9b0c1d2
Revises: q6e7f8a9b0c1
"""
from alembic import op
import sqlalchemy as sa


revision = "r7f8a9b0c1d2"
down_revision = "q6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_user", sa.Column("vision_consent_granted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("app_user", sa.Column("vision_consent_version", sa.String(), nullable=True))
    op.alter_column("app_user", "vision_consent_granted", server_default=None)


def downgrade() -> None:
    op.drop_column("app_user", "vision_consent_version")
    op.drop_column("app_user", "vision_consent_granted")
