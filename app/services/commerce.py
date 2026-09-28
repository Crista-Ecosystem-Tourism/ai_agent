from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.commerce import AffiliateOffer, CommerceEntitlement, CommerceProduct


class CommerceCheckoutUnavailableError(RuntimeError):
    pass


class CommerceService:
    """Read the server-owned catalog and rights without creating a pretend payment flow."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock=lambda: datetime.now(timezone.utc),
    ):
        self.session_factory = session_factory
        self._clock = clock

    async def list_catalog(self) -> dict:
        async with self.session_factory() as db:
            products = (await db.execute(
                select(CommerceProduct)
                .where(CommerceProduct.status == "active")
                .order_by(CommerceProduct.kind, CommerceProduct.sku)
            )).scalars().all()
            return {
                "checkout_available": False,
                "products": [self._product_payload(product) for product in products],
            }

    async def list_affiliate_offers(self) -> list[dict]:
        async with self.session_factory() as db:
            rows = (await db.scalars(select(AffiliateOffer).where(AffiliateOffer.status == "active").order_by(AffiliateOffer.partner, AffiliateOffer.title))).all()
        return [{"id": row.id, "partner": row.partner, "title": row.title, "destination_url": row.destination_url, "terms_url": row.terms_url} for row in rows]

    async def list_entitlements(self, user_id: str) -> dict:
        now = self._clock()
        async with self.session_factory() as db:
            rows = (await db.execute(
                select(CommerceEntitlement)
                .where(
                    CommerceEntitlement.user_id == user_id,
                    CommerceEntitlement.status == "active",
                    CommerceEntitlement.starts_at <= now,
                    or_(CommerceEntitlement.ends_at.is_(None), CommerceEntitlement.ends_at > now),
                )
                .order_by(CommerceEntitlement.entitlement_key, CommerceEntitlement.starts_at)
            )).scalars().all()
            return {
                "checkout_available": False,
                "entitlements": [self._entitlement_payload(row) for row in rows],
            }

    async def start_checkout(self, user_id: str, sku: str) -> None:
        del user_id, sku
        raise CommerceCheckoutUnavailableError

    @staticmethod
    def _product_payload(product: CommerceProduct) -> dict:
        return {
            "sku": product.sku,
            "kind": product.kind,
            "title": product.title,
            "description": product.description,
            "price_minor": product.price_minor,
            "currency": product.currency,
        }

    @staticmethod
    def _entitlement_payload(entitlement: CommerceEntitlement) -> dict:
        return {
            "key": entitlement.entitlement_key,
            "starts_at": entitlement.starts_at.isoformat(),
            "ends_at": entitlement.ends_at.isoformat() if entitlement.ends_at else None,
        }
