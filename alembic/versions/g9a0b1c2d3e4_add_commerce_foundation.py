"""Add provider-neutral commerce catalog, order, event and entitlement records."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commerce_product",
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_product_ref", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('subscription', 'expedition', 'energy_pack', 'cosmetic')", name="commerce_product_kind"),
        sa.CheckConstraint("price_minor >= 0", name="commerce_product_nonnegative_price"),
        sa.CheckConstraint("char_length(currency) = 3", name="commerce_product_currency_code"),
        sa.CheckConstraint("status IN ('draft', 'active', 'archived')", name="commerce_product_status"),
        sa.PrimaryKeyConstraint("sku"),
    )
    op.create_index("idx_commerce_product_active", "commerce_product", ["status", "kind"])

    op.create_table(
        "commerce_order",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("product_sku", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=48), nullable=True),
        sa.Column("provider_order_ref", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')", name="commerce_order_status"),
        sa.CheckConstraint("price_minor >= 0", name="commerce_order_nonnegative_price"),
        sa.CheckConstraint("char_length(currency) = 3", name="commerce_order_currency_code"),
        sa.CheckConstraint(
            "(provider IS NULL AND provider_order_ref IS NULL) OR (provider IS NOT NULL AND provider_order_ref IS NOT NULL)",
            name="commerce_order_provider_reference_pair",
        ),
        sa.ForeignKeyConstraint(["product_sku"], ["commerce_product.sku"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_order_ref", name="uq_commerce_order_provider_reference"),
    )
    op.create_index("idx_commerce_order_user_status", "commerce_order", ["user_id", "status", "updated_at"])

    op.create_table(
        "commerce_entitlement",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("entitlement_key", sa.String(length=80), nullable=False),
        sa.Column("source_order_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'expired', 'revoked')", name="commerce_entitlement_status"),
        sa.CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="commerce_entitlement_positive_window"),
        sa.CheckConstraint(
            "(status = 'revoked' AND revoked_at IS NOT NULL) OR (status <> 'revoked' AND revoked_at IS NULL)",
            name="commerce_entitlement_revocation_state",
        ),
        sa.ForeignKeyConstraint(["source_order_id"], ["commerce_order.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_commerce_entitlement_user_status", "commerce_entitlement", ["user_id", "status", "starts_at"])

    op.create_table(
        "commerce_payment_event",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("provider_event_ref", sa.String(length=160), nullable=False),
        sa.Column("order_id", sa.String(length=32), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["commerce_order.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_ref", name="uq_commerce_payment_event_provider_reference"),
    )
    op.create_index("idx_commerce_payment_event_order", "commerce_payment_event", ["order_id", "received_at"])


def downgrade() -> None:
    op.drop_index("idx_commerce_payment_event_order", table_name="commerce_payment_event")
    op.drop_table("commerce_payment_event")
    op.drop_index("idx_commerce_entitlement_user_status", table_name="commerce_entitlement")
    op.drop_table("commerce_entitlement")
    op.drop_index("idx_commerce_order_user_status", table_name="commerce_order")
    op.drop_table("commerce_order")
    op.drop_index("idx_commerce_product_active", table_name="commerce_product")
    op.drop_table("commerce_product")
