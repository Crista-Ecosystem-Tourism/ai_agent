from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from app.security.deps import get_current_user
from app.dependencies import get_suitcase_service
from app.services.suitcase import SuitcaseService
from app.api.schemas import (
    SuitcaseWorkspaceOut,
    SuitcaseTripCreate,
    SuitcaseTripPatch,
    SuitcaseTripOut,
    SuitcaseExpenseCreate,
    SuitcaseExpensePatch,
    SuitcaseExpenseOut,
    SuitcaseGoalCreate,
    SuitcaseGoalPatch,
    SuitcaseGoalOut,
)


router = APIRouter(prefix="/suitcase", tags=["suitcase"])


@router.get("/workspace", response_model=SuitcaseWorkspaceOut)
async def suitcase_workspace(
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    data = await srv.get_workspace(user["sub"])
    return SuitcaseWorkspaceOut(
        trips=[SuitcaseTripOut(**t) for t in data["trips"]],
        expenses=[SuitcaseExpenseOut(**e) for e in data["expenses"]],
        goals=[SuitcaseGoalOut(**g) for g in data["goals"]],
    )


@router.post("/trips", response_model=SuitcaseTripOut)
async def create_trip(
    payload: SuitcaseTripCreate,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    row = await srv.create_trip(user["sub"], payload.model_dump(exclude_unset=True))
    return SuitcaseTripOut(**row)


@router.patch("/trips/{trip_id}", response_model=SuitcaseTripOut)
async def patch_trip(
    trip_id: str,
    payload: SuitcaseTripPatch,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    row = await srv.update_trip(trip_id, user["sub"], patch)
    if not row:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Поездка не найдена")
    return SuitcaseTripOut(**row)


@router.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    ok = await srv.delete_trip(trip_id, user["sub"])
    if not ok:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Поездка не найдена")
    return {"ok": True}


@router.post("/trips/{trip_id}/expenses", response_model=SuitcaseExpenseOut)
async def create_expense(
    trip_id: str,
    payload: SuitcaseExpenseCreate,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    row = await srv.create_expense(user["sub"], trip_id, payload.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Поездка не найдена")
    return SuitcaseExpenseOut(**row)


@router.patch("/expenses/{expense_id}", response_model=SuitcaseExpenseOut)
async def patch_expense(
    expense_id: str,
    payload: SuitcaseExpensePatch,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    row = await srv.update_expense(expense_id, user["sub"], patch)
    if not row:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Расход не найден")
    return SuitcaseExpenseOut(**row)


@router.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    ok = await srv.delete_expense(expense_id, user["sub"])
    if not ok:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Расход не найден")
    return {"ok": True}


@router.post("/goals", response_model=SuitcaseGoalOut)
async def create_goal(
    payload: SuitcaseGoalCreate,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    row = await srv.create_goal(user["sub"], payload.model_dump(exclude_unset=True))
    return SuitcaseGoalOut(**row)


@router.patch("/goals/{goal_id}", response_model=SuitcaseGoalOut)
async def patch_goal(
    goal_id: str,
    payload: SuitcaseGoalPatch,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    row = await srv.update_goal(goal_id, user["sub"], patch)
    if not row:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Цель не найдена")
    return SuitcaseGoalOut(**row)


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: str,
    user=Depends(get_current_user),
    srv: SuitcaseService = Depends(get_suitcase_service),
):
    ok = await srv.delete_goal(goal_id, user["sub"])
    if not ok:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Цель не найдена")
    return {"ok": True}
