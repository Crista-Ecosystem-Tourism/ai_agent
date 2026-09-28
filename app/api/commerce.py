"""Server-owned catalog and entitlements. Hosted checkout is intentionally unavailable until configured."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import RedirectResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_503_SERVICE_UNAVAILABLE

from app.dependencies import get_commerce_service
from app.security.deps import get_current_user
from app.services.commerce import CommerceCheckoutUnavailableError, CommerceNotFoundError, CommerceService, CommerceValidationError


router = APIRouter(prefix="/commerce", tags=["commerce"])


class AffiliateOfferCreateIn(BaseModel):
    partner: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    destination_url: str = Field(min_length=8, max_length=2048, pattern=r"^https://")
    terms_url: str = Field(min_length=8, max_length=2048, pattern=r"^https://")
    status: Literal["draft", "active", "archived"] = "draft"


class AffiliateOfferUpdateIn(BaseModel):
    partner: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    destination_url: str | None = Field(default=None, min_length=8, max_length=2048, pattern=r"^https://")
    terms_url: str | None = Field(default=None, min_length=8, max_length=2048, pattern=r"^https://")
    status: Literal["draft", "active", "archived"] | None = None


class CommerceProductCreateIn(BaseModel):
    sku: str = Field(min_length=2, max_length=80)
    kind: Literal["subscription", "expedition", "energy_pack", "cosmetic"]
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    price_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    provider_product_ref: str | None = Field(default=None, max_length=160)


class CommerceProductUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    price_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    provider_product_ref: str | None = Field(default=None, max_length=160)
    status: Literal["draft", "active", "archived"] | None = None


def _affiliate_error(error: Exception) -> HTTPException:
    if isinstance(error, PermissionError):
        return HTTPException(status_code=HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, CommerceNotFoundError):
        return HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Партнёрское предложение не найдено")
    return HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(error))


def _catalog_error(error: Exception) -> HTTPException:
    if isinstance(error, PermissionError):
        return HTTPException(status_code=HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, CommerceNotFoundError):
        return HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Позиция каталога не найдена")
    return HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/catalog")
async def list_catalog(commerce: CommerceService = Depends(get_commerce_service)):
    return await commerce.list_catalog()


@router.get("/editor/catalog")
async def list_catalog_for_editor(
    user: dict = Depends(get_current_user),
    commerce: CommerceService = Depends(get_commerce_service),
):
    try:
        return await commerce.list_catalog_for_editor(user["sub"])
    except PermissionError as error:
        raise _catalog_error(error)


@router.post("/editor/catalog")
async def create_catalog_product(
    payload: CommerceProductCreateIn,
    user: dict = Depends(get_current_user),
    commerce: CommerceService = Depends(get_commerce_service),
):
    try:
        return await commerce.create_catalog_product(user["sub"], payload.model_dump())
    except (PermissionError, CommerceValidationError) as error:
        raise _catalog_error(error)


@router.patch("/editor/catalog/{sku}")
async def update_catalog_product(
    sku: str,
    payload: CommerceProductUpdateIn,
    user: dict = Depends(get_current_user),
    commerce: CommerceService = Depends(get_commerce_service),
):
    try:
        return await commerce.update_catalog_product(user["sub"], sku, payload.model_dump(exclude_unset=True))
    except (PermissionError, CommerceNotFoundError, CommerceValidationError) as error:
        raise _catalog_error(error)


@router.get("/affiliate-offers")
async def list_affiliate_offers(commerce: CommerceService = Depends(get_commerce_service)):
    return await commerce.list_affiliate_offers()


@router.get("/editor/affiliate-offers")
async def list_affiliate_offers_for_editor(
    user: dict = Depends(get_current_user),
    commerce: CommerceService = Depends(get_commerce_service),
):
    try:
        return await commerce.list_affiliate_offers_for_editor(user["sub"])
    except PermissionError as error:
        raise _affiliate_error(error)


@router.post("/editor/affiliate-offers")
async def create_affiliate_offer(
    payload: AffiliateOfferCreateIn,
    user: dict = Depends(get_current_user),
    commerce: CommerceService = Depends(get_commerce_service),
):
    try:
        return await commerce.create_affiliate_offer(user["sub"], payload.model_dump())
    except (PermissionError, CommerceValidationError) as error:
        raise _affiliate_error(error)


@router.patch("/editor/affiliate-offers/{offer_id}")
async def update_affiliate_offer(
    offer_id: str,
    payload: AffiliateOfferUpdateIn,
    user: dict = Depends(get_current_user),
    commerce: CommerceService = Depends(get_commerce_service),
):
    try:
        return await commerce.update_affiliate_offer(
            user["sub"], offer_id, payload.model_dump(exclude_unset=True)
        )
    except (PermissionError, CommerceNotFoundError, CommerceValidationError) as error:
        raise _affiliate_error(error)


@router.get("/affiliate-offers/{offer_id}/go")
async def follow_affiliate_offer(
    offer_id: str,
    commerce: CommerceService = Depends(get_commerce_service),
):
    destination_url = await commerce.register_affiliate_offer_click(offer_id)
    if destination_url is None:
        raise HTTPException(status_code=404, detail="Партнёрское предложение не найдено")
    return RedirectResponse(url=destination_url, status_code=307)


@router.get("/entitlements")
async def list_entitlements(
    user: dict = Depends(get_current_user),
    commerce: CommerceService = Depends(get_commerce_service),
):
    return await commerce.list_entitlements(user["sub"])


@router.post("/checkout/{sku}")
async def start_checkout(
    sku: str,
    user: dict = Depends(get_current_user),
    commerce: CommerceService = Depends(get_commerce_service),
):
    try:
        await commerce.start_checkout(user["sub"], sku)
    except CommerceCheckoutUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Онлайн-оплата ещё не подключена",
        )
