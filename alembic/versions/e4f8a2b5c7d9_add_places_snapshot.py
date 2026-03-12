"""add_places_snapshot_to_chat_session

Revision ID: e4f8a2b5c7d9
Revises: d3e7f1a2b4c6
Create Date: 2026-03-12 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'e4f8a2b5c7d9'
down_revision: Union[str, Sequence[str], None] = 'd3e7f1a2b4c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_session', sa.Column('places_snapshot', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('chat_session', 'places_snapshot')
