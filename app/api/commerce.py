"""Server-owned catalog and entitlements. Hosted checkout is intentionally unavailable until configured."""

from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from app.dependencies import get_commerce_service
from app.security.deps import get_current_user
from app.services.commerce import CommerceCheckoutUnavailableError, CommerceService


router = APIRouter(prefix="/commerce", tags=["commerce"])


@router.get("/catalog")
async def list_catalog(commerce: CommerceService = Depends(get_commerce_service)):
    return await commerce.list_catalog()


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
