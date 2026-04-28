"""add_suitcase_tables

Revision ID: f7a1b2c3d4e5
Revises: e4f8a2b5c7d9
Create Date: 2026-04-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'f7a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e4f8a2b5c7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'suitcase_trip',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('country', sa.String(length=200), nullable=False),
        sa.Column('city', sa.String(length=200), nullable=False),
        sa.Column('start_date', sa.String(length=32), nullable=False),
        sa.Column('end_date', sa.String(length=32), nullable=False),
        sa.Column('image', sa.String(length=1024), nullable=True),
        sa.Column('mood', sa.String(length=100), nullable=True),
        sa.Column('route_json', sa.Text(), nullable=True),
        sa.Column('impressions', sa.Text(), nullable=True),
        sa.Column('photos', JSONB, nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_suitcase_trip_user_id', 'suitcase_trip', ['user_id'])

    op.create_table(
        'suitcase_expense',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('trip_id', sa.String(), sa.ForeignKey('suitcase_trip.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('date', sa.String(length=32), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_suitcase_expense_trip_id', 'suitcase_expense', ['trip_id'])

    op.create_table(
        'suitcase_goal',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('current', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('color', sa.String(length=32), nullable=False, server_default='#007AFF'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_suitcase_goal_user_id', 'suitcase_goal', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_suitcase_goal_user_id', table_name='suitcase_goal')
    op.drop_table('suitcase_goal')
    op.drop_index('ix_suitcase_expense_trip_id', table_name='suitcase_expense')
    op.drop_table('suitcase_expense')
    op.drop_index('ix_suitcase_trip_user_id', table_name='suitcase_trip')
    op.drop_table('suitcase_trip')
