from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.security.deps import get_current_user
from app.dependencies import get_price_service
from app.services.prices import PriceService
router = APIRouter(prefix="/prices", tags=["prices"])
class BudgetCheckIn(BaseModel):
    budget_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    subject_keys: list[str] = Field(min_length=1, max_length=100)

class BudgetPlanIn(BaseModel):
    budget_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    required_subject_keys: list[str] = Field(default_factory=list, max_length=100)
    optional_subject_keys: list[str] = Field(default_factory=list, max_length=100)
class PriceWatchIn(BaseModel):
    subject_key: str = Field(min_length=1, max_length=200)
    threshold_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

@router.post("/budget-check")
async def budget_check(payload: BudgetCheckIn, prices: PriceService = Depends(get_price_service)):
    return await prices.evaluate_budget(payload.budget_minor, payload.currency.upper(), payload.subject_keys)

@router.post("/budget-plan")
async def budget_plan(payload: BudgetPlanIn, prices: PriceService = Depends(get_price_service)):
    return await prices.plan_budget(payload.budget_minor, payload.currency.upper(), payload.required_subject_keys, payload.optional_subject_keys)

@router.get("/watches")
async def list_watches(user: dict = Depends(get_current_user), prices: PriceService = Depends(get_price_service)):
    return await prices.list_watches(user["sub"])

@router.get("/alerts")
async def list_alerts(user: dict = Depends(get_current_user), prices: PriceService = Depends(get_price_service)):
    return await prices.list_alerts(user["sub"])

@router.post("/watches")
async def subscribe_watch(payload: PriceWatchIn, user: dict = Depends(get_current_user), prices: PriceService = Depends(get_price_service)):
    return await prices.subscribe(user["sub"], payload.subject_key, payload.threshold_minor, payload.currency.upper())

@router.delete("/watches/{watch_id}")
async def unsubscribe_watch(watch_id: str, user: dict = Depends(get_current_user), prices: PriceService = Depends(get_price_service)):
    if not await prices.unsubscribe(user["sub"], watch_id):
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    return {"ok": True}

@router.get("/{subject_key}")
async def latest_price(subject_key: str, prices: PriceService = Depends(get_price_service)):
    return await prices.latest(subject_key)
