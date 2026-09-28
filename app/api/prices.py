from fastapi import APIRouter, Depends
from app.dependencies import get_price_service
from app.services.prices import PriceService
router = APIRouter(prefix="/prices", tags=["prices"])
@router.get("/{subject_key}")
async def latest_price(subject_key: str, prices: PriceService = Depends(get_price_service)):
    return await prices.latest(subject_key)
