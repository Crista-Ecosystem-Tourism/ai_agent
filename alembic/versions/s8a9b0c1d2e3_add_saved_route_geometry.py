"""store generated route geometry separately from place graphs

Revision ID: s8a9b0c1d2e3
Revises: r7f8a9b0c1d2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "s8a9b0c1d2e3"
down_revision = "r7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("saved_route", sa.Column("route_geojson", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("saved_route", "route_geojson")
