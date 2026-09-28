"""Add explicit consent boundary for future presence verification.

Revision ID: b0c1d2e3f4a5
Revises: a0b1c2d3e4f5
"""
from alembic import op
import sqlalchemy as sa


revision = "b0c1d2e3f4a5"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_user", sa.Column("presence_consent_granted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("app_user", sa.Column("presence_consent_version", sa.String(), nullable=True))
    op.alter_column("app_user", "presence_consent_granted", server_default=None)


def downgrade() -> None:
    op.drop_column("app_user", "presence_consent_version")
    op.drop_column("app_user", "presence_consent_granted")
