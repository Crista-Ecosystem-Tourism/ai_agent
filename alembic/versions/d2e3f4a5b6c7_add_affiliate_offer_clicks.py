"""Add privacy-minimal affiliate offer click records.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
"""
from alembic import op
import sqlalchemy as sa


revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "affiliate_offer_click",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("offer_id", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["affiliate_offer.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_affiliate_offer_click_offer_time",
        "affiliate_offer_click",
        ["offer_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_affiliate_offer_click_offer_time", table_name="affiliate_offer_click")
    op.drop_table("affiliate_offer_click")
