"""add Wiki editor role

Revision ID: h7c8d9e0f1a2
Revises: g6b7c8d9e0f1
Create Date: 2026-09-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "g6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_user", sa.Column("is_editor", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("app_user", "is_editor", server_default=None)


def downgrade() -> None:
    op.drop_column("app_user", "is_editor")
