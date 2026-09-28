"""Server-owned catalog and entitlements. Hosted checkout is intentionally unavailable until configured."""

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import RedirectResponse
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from app.dependencies import get_commerce_service
from app.security.deps import get_current_user
from app.services.commerce import CommerceCheckoutUnavailableError, CommerceService


router = APIRouter(prefix="/commerce", tags=["commerce"])


@router.get("/catalog")
async def list_catalog(commerce: CommerceService = Depends(get_commerce_service)):
    return await commerce.list_catalog()


@router.get("/affiliate-offers")
async def list_affiliate_offers(commerce: CommerceService = Depends(get_commerce_service)):
    return await commerce.list_affiliate_offers()


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
