from __future__ import annotations

from datetime import datetime, timezone
import re
import uuid
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.auth import User
from app.db.models.commerce import AffiliateOffer, AffiliateOfferClick, CommerceEntitlement, CommerceProduct


class CommerceCheckoutUnavailableError(RuntimeError):
    pass


class CommerceNotFoundError(RuntimeError):
    pass


class CommerceValidationError(ValueError):
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

    async def list_catalog_for_editor(self, editor_id: str) -> list[dict]:
        await self._require_editor(editor_id)
        async with self.session_factory() as db:
            products = (await db.scalars(select(CommerceProduct).order_by(CommerceProduct.updated_at.desc()))).all()
        return [self._editor_product_payload(product) for product in products]

    async def create_catalog_product(self, editor_id: str, payload: dict[str, Any]) -> dict:
        await self._require_editor(editor_id)
        now = self._clock()
        product = CommerceProduct(
            sku=self._sku(payload["sku"]),
            kind=payload["kind"],
            title=self._text(payload["title"], "Название", 160),
            description=self._optional_text(payload.get("description"), 4000),
            price_minor=payload["price_minor"],
            currency=self._currency(payload["currency"]),
            status="draft",
            provider_product_ref=self._optional_text(payload.get("provider_product_ref"), 160),
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as db:
            if await db.get(CommerceProduct, product.sku) is not None:
                raise CommerceValidationError("SKU уже существует")
            db.add(product)
            await db.commit()
        return self._editor_product_payload(product)

    async def update_catalog_product(self, editor_id: str, sku: str, payload: dict[str, Any]) -> dict:
        await self._require_editor(editor_id)
        if not payload:
            raise CommerceValidationError("Не переданы поля для изменения")
        async with self.session_factory() as db:
            product = await db.get(CommerceProduct, sku)
            if product is None:
                raise CommerceNotFoundError(sku)
            if "title" in payload:
                product.title = self._text(payload["title"], "Название", 160)
            if "description" in payload:
                product.description = self._optional_text(payload["description"], 4000)
            if "price_minor" in payload:
                product.price_minor = payload["price_minor"]
            if "currency" in payload:
                product.currency = self._currency(payload["currency"])
            if "provider_product_ref" in payload:
                product.provider_product_ref = self._optional_text(payload["provider_product_ref"], 160)
            if "status" in payload:
                product.status = payload["status"]
            if product.status == "active" and not product.provider_product_ref:
                raise CommerceValidationError("Для active-позиции нужен provider reference")
            product.updated_at = self._clock()
            await db.commit()
        return self._editor_product_payload(product)

    async def list_affiliate_offers(self) -> list[dict]:
        async with self.session_factory() as db:
            rows = (await db.scalars(select(AffiliateOffer).where(AffiliateOffer.status == "active").order_by(AffiliateOffer.partner, AffiliateOffer.title))).all()
        return [{"id": row.id, "partner": row.partner, "title": row.title, "destination_url": row.destination_url, "terms_url": row.terms_url} for row in rows]

    async def list_affiliate_offers_for_editor(self, editor_id: str) -> list[dict]:
        await self._require_editor(editor_id)
        async with self.session_factory() as db:
            rows = (await db.scalars(select(AffiliateOffer).order_by(AffiliateOffer.updated_at.desc()))).all()
        return [self._affiliate_offer_payload(row) for row in rows]

    async def create_affiliate_offer(self, editor_id: str, payload: dict[str, Any]) -> dict:
        await self._require_editor(editor_id)
        now = self._clock()
        offer = AffiliateOffer(
            id=uuid.uuid4().hex,
            partner=self._text(payload["partner"], "Партнёр", 120),
            title=self._text(payload["title"], "Название", 160),
            destination_url=self._https_url(payload["destination_url"], "Целевая ссылка"),
            terms_url=self._https_url(payload["terms_url"], "Ссылка на условия"),
            status=payload.get("status", "draft"),
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as db:
            db.add(offer)
            await db.commit()
        return self._affiliate_offer_payload(offer)

    async def update_affiliate_offer(self, editor_id: str, offer_id: str, payload: dict[str, Any]) -> dict:
        await self._require_editor(editor_id)
        if not payload:
            raise CommerceValidationError("Не переданы поля для изменения")
        async with self.session_factory() as db:
            offer = await db.get(AffiliateOffer, offer_id)
            if offer is None:
                raise CommerceNotFoundError(offer_id)
            if "partner" in payload:
                offer.partner = self._text(payload["partner"], "Партнёр", 120)
            if "title" in payload:
                offer.title = self._text(payload["title"], "Название", 160)
            if "destination_url" in payload:
                offer.destination_url = self._https_url(payload["destination_url"], "Целевая ссылка")
            if "terms_url" in payload:
                offer.terms_url = self._https_url(payload["terms_url"], "Ссылка на условия")
            if "status" in payload:
                offer.status = payload["status"]
            offer.updated_at = self._clock()
            await db.commit()
        return self._affiliate_offer_payload(offer)

    async def register_affiliate_offer_click(self, offer_id: str) -> str | None:
        """Return an active destination and retain no visitor identifiers for click measurement."""
        now = self._clock()
        async with self.session_factory() as db:
            offer = await db.scalar(
                select(AffiliateOffer).where(
                    AffiliateOffer.id == offer_id,
                    AffiliateOffer.status == "active",
                )
            )
            if offer is None:
                return None
            db.add(AffiliateOfferClick(id=uuid.uuid4().hex, offer_id=offer.id, occurred_at=now))
            await db.commit()
            return offer.destination_url

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

    @classmethod
    def _editor_product_payload(cls, product: CommerceProduct) -> dict:
        return {
            **cls._product_payload(product),
            "status": product.status,
            "provider_product_ref": product.provider_product_ref,
            "updated_at": product.updated_at.isoformat(),
        }

    @staticmethod
    def _entitlement_payload(entitlement: CommerceEntitlement) -> dict:
        return {
            "key": entitlement.entitlement_key,
            "starts_at": entitlement.starts_at.isoformat(),
            "ends_at": entitlement.ends_at.isoformat() if entitlement.ends_at else None,
        }

    async def _require_editor(self, user_id: str) -> None:
        async with self.session_factory() as db:
            user = await db.get(User, user_id)
            if user is None or not user.is_editor:
                raise PermissionError("Требуется роль редактора")

    @staticmethod
    def _text(value: Any, label: str, max_length: int) -> str:
        cleaned = value.strip() if isinstance(value, str) else ""
        if not cleaned:
            raise CommerceValidationError(f"{label} не может быть пустым")
        return cleaned[:max_length]

    @staticmethod
    def _optional_text(value: Any, max_length: int) -> str | None:
        cleaned = value.strip()[:max_length] if isinstance(value, str) else ""
        return cleaned or None

    @staticmethod
    def _sku(value: Any) -> str:
        cleaned = value.strip().lower() if isinstance(value, str) else ""
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,79}", cleaned):
            raise CommerceValidationError("SKU должен содержать 2–80 строчных букв, цифр, _ или -")
        return cleaned

    @staticmethod
    def _currency(value: Any) -> str:
        cleaned = value.strip().upper() if isinstance(value, str) else ""
        if not re.fullmatch(r"[A-Z]{3}", cleaned):
            raise CommerceValidationError("Валюта должна состоять из трёх латинских букв")
        return cleaned

    @staticmethod
    def _https_url(value: Any, label: str) -> str:
        cleaned = value.strip() if isinstance(value, str) else ""
        parsed = urlsplit(cleaned)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise CommerceValidationError(f"{label} должна быть HTTPS-ссылкой")
        return cleaned

    @staticmethod
    def _affiliate_offer_payload(offer: AffiliateOffer) -> dict:
        return {
            "id": offer.id,
            "partner": offer.partner,
            "title": offer.title,
            "destination_url": offer.destination_url,
            "terms_url": offer.terms_url,
            "status": offer.status,
            "updated_at": offer.updated_at.isoformat(),
        }
