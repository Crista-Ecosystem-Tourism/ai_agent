"""Add contract-backed affiliate offers.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("affiliate_offer", sa.Column("id", sa.String(length=32), primary_key=True), sa.Column("partner", sa.String(length=120), nullable=False), sa.Column("title", sa.String(length=160), nullable=False), sa.Column("destination_url", sa.String(length=2048), nullable=False), sa.Column("terms_url", sa.String(length=2048), nullable=False), sa.Column("status", sa.String(length=16), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("status IN ('draft', 'active', 'archived')", name="affiliate_offer_status"))

def downgrade() -> None:
    op.drop_table("affiliate_offer")
