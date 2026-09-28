from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class CommerceProduct(Base, TimestampMixin):
    """A provider-neutral catalog entry. Draft products are never returned to clients."""

    __tablename__ = "commerce_product"

    sku: Mapped[str] = mapped_column(String(80), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    provider_product_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)

    __table_args__ = (
        CheckConstraint("kind IN ('subscription', 'expedition', 'energy_pack', 'cosmetic')", name="commerce_product_kind"),
        CheckConstraint("price_minor >= 0", name="commerce_product_nonnegative_price"),
        CheckConstraint("char_length(currency) = 3", name="commerce_product_currency_code"),
        CheckConstraint("status IN ('draft', 'active', 'archived')", name="commerce_product_status"),
        Index("idx_commerce_product_active", "status", "kind"),
    )


class CommerceOrder(Base, TimestampMixin):
    """Provider order state; client code never changes this row directly."""

    __tablename__ = "commerce_order"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    product_sku: Mapped[str] = mapped_column(ForeignKey("commerce_product.sku", ondelete="RESTRICT"), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(48), nullable=True)
    provider_order_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')", name="commerce_order_status"),
        CheckConstraint("price_minor >= 0", name="commerce_order_nonnegative_price"),
        CheckConstraint("char_length(currency) = 3", name="commerce_order_currency_code"),
        CheckConstraint(
            "(provider IS NULL AND provider_order_ref IS NULL) OR (provider IS NOT NULL AND provider_order_ref IS NOT NULL)",
            name="commerce_order_provider_reference_pair",
        ),
        UniqueConstraint("provider", "provider_order_ref", name="uq_commerce_order_provider_reference"),
        Index("idx_commerce_order_user_status", "user_id", "status", "updated_at"),
    )


class CommerceEntitlement(Base, TimestampMixin):
    """A time-bound server-owned right granted only from a settled order."""

    __tablename__ = "commerce_entitlement"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    entitlement_key: Mapped[str] = mapped_column(String(80), nullable=False)
    source_order_id: Mapped[str] = mapped_column(ForeignKey("commerce_order.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'expired', 'revoked')", name="commerce_entitlement_status"),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="commerce_entitlement_positive_window"),
        CheckConstraint(
            "(status = 'revoked' AND revoked_at IS NOT NULL) OR (status <> 'revoked' AND revoked_at IS NULL)",
            name="commerce_entitlement_revocation_state",
        ),
        Index("idx_commerce_entitlement_user_status", "user_id", "status", "starts_at"),
    )


class CommercePaymentEvent(Base):
    """Deduplicated webhook receipt metadata; raw provider payloads are intentionally not retained."""

    __tablename__ = "commerce_payment_event"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    provider_event_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("commerce_order.id", ondelete="RESTRICT"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("provider", "provider_event_ref", name="uq_commerce_payment_event_provider_reference"),
        Index("idx_commerce_payment_event_order", "order_id", "received_at"),
    )


class AffiliateOffer(Base, TimestampMixin):
    """A contract-backed external offer; inactive rows never reach clients."""
    __tablename__ = "affiliate_offer"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    partner: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    terms_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    __table_args__ = (CheckConstraint("status IN ('draft', 'active', 'archived')", name="affiliate_offer_status"),)


class AffiliateOfferClick(Base):
    """Minimal aggregate-friendly record of a transition to an active affiliate offer."""

    __tablename__ = "affiliate_offer_click"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    offer_id: Mapped[str] = mapped_column(
        ForeignKey("affiliate_offer.id", ondelete="CASCADE"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("idx_affiliate_offer_click_offer_time", "offer_id", "occurred_at"),)
