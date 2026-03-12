"""add_travel_data_persistence

Revision ID: d3e7f1a2b4c6
Revises: 8db244568f74
Create Date: 2026-03-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'd3e7f1a2b4c6'
down_revision: Union[str, Sequence[str], None] = '8db244568f74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add JSONB columns to chat_session
    op.add_column('chat_session', sa.Column('place_ratings', JSONB, nullable=True))
    op.add_column('chat_session', sa.Column('graph_geojson', JSONB, nullable=True))

    # Create saved_route table
    op.create_table(
        'saved_route',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('destination', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), sa.ForeignKey('chat_session.id'), nullable=True),
        sa.Column('places', JSONB, nullable=False),
        sa.Column('graph_geojson', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_saved_route_user', 'saved_route', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_saved_route_user', table_name='saved_route')
    op.drop_table('saved_route')
    op.drop_column('chat_session', 'graph_geojson')
    op.drop_column('chat_session', 'place_ratings')
