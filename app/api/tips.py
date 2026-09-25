"""Authenticated user tips attached to published quest locations."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_tip_service
from app.security.deps import get_current_user
from app.services.tips import (
    TipDuplicateReportError,
    TipNotFoundError,
    TipPermissionError,
    TipRateLimitError,
    TipService,
    TipTargetUnavailableError,
)


router = APIRouter(prefix="/tips", tags=["tips"])


class TipDraftIn(BaseModel):
    quest_id: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=10, max_length=1200)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return " ".join(value.split())


class TipTextIn(BaseModel):
    text: str = Field(min_length=10, max_length=1200)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return " ".join(value.split())


class TipReportIn(BaseModel):
    reason: Literal["inaccurate", "unsafe", "spam", "copyright", "other"]
    details: str | None = Field(default=None, max_length=500)


class TipDecisionIn(BaseModel):
    decision: Literal["publish", "reject", "hide"]
    note: str | None = Field(default=None, max_length=500)


class TipReportResolutionIn(BaseModel):
    resolution: Literal["dismiss", "hide_tip"]
    note: str | None = Field(default=None, max_length=500)


@router.get("/quest/{quest_id}")
async def list_published_tips(quest_id: str, tips: TipService = Depends(get_tip_service)):
    try:
        return await tips.list_published(quest_id)
    except TipTargetUnavailableError:
        raise HTTPException(status_code=404, detail="Опубликованная точка не найдена")


@router.get("/mine")
async def list_my_tips(user: dict = Depends(get_current_user), tips: TipService = Depends(get_tip_service)):
    return await tips.list_mine(user["sub"])


@router.post("", status_code=201)
async def create_tip_draft(
    payload: TipDraftIn,
    user: dict = Depends(get_current_user),
    tips: TipService = Depends(get_tip_service),
):
    try:
        return await tips.create_draft(user["sub"], payload.quest_id, payload.text)
    except TipTargetUnavailableError:
        raise HTTPException(status_code=404, detail="Опубликованная точка не найдена")
    except TipRateLimitError:
        raise HTTPException(status_code=429, detail="Слишком много черновиков заметок")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.put("/{tip_id}")
async def update_tip_draft(
    tip_id: str, payload: TipTextIn, user: dict = Depends(get_current_user),
    tips: TipService = Depends(get_tip_service),
):
    try:
        return await tips.update_draft(user["sub"], tip_id, payload.text)
    except TipNotFoundError:
        raise HTTPException(status_code=404, detail="Черновик не найден")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.delete("/{tip_id}", status_code=204)
async def delete_tip_draft(
    tip_id: str, user: dict = Depends(get_current_user),
    tips: TipService = Depends(get_tip_service),
):
    try:
        await tips.delete_draft(user["sub"], tip_id)
    except TipNotFoundError:
        raise HTTPException(status_code=404, detail="Черновик не найден")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return Response(status_code=204)


@router.post("/{tip_id}/submit")
async def submit_tip(
    tip_id: str, user: dict = Depends(get_current_user), tips: TipService = Depends(get_tip_service),
):
    try:
        return await tips.submit(user["sub"], tip_id)
    except TipNotFoundError:
        raise HTTPException(status_code=404, detail="Черновик не найден")
    except TipRateLimitError:
        raise HTTPException(status_code=429, detail="Достигнут лимит отправки заметок: не более 5 за 24 часа")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/{tip_id}/report", status_code=201)
async def report_tip(
    tip_id: str, payload: TipReportIn, user: dict = Depends(get_current_user),
    tips: TipService = Depends(get_tip_service),
):
    try:
        return await tips.report(user["sub"], tip_id, payload.reason, payload.details)
    except TipNotFoundError:
        raise HTTPException(status_code=404, detail="Опубликованная заметка не найдена")
    except TipPermissionError:
        raise HTTPException(status_code=403, detail="Нельзя пожаловаться на собственную заметку")
    except TipDuplicateReportError:
        raise HTTPException(status_code=409, detail="Вы уже отправляли жалобу на эту заметку")
    except TipRateLimitError:
        raise HTTPException(status_code=429, detail="Достигнут лимит отправки жалоб: не более 10 за 24 часа")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/moderation/review")
async def get_tip_review_queue(user: dict = Depends(get_current_user), tips: TipService = Depends(get_tip_service)):
    try:
        return await tips.list_review_queue(user["sub"])
    except TipPermissionError:
        raise HTTPException(status_code=403, detail="Требуется роль редактора")


@router.post("/moderation/{tip_id}/decision")
async def decide_tip(
    tip_id: str, payload: TipDecisionIn, user: dict = Depends(get_current_user),
    tips: TipService = Depends(get_tip_service),
):
    try:
        return await tips.decide(user["sub"], tip_id, payload.decision, payload.note)
    except TipPermissionError:
        raise HTTPException(status_code=403, detail="Требуется роль редактора")
    except TipNotFoundError:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.get("/moderation/reports")
async def get_tip_reports(
    pending_only: bool = True,
    user: dict = Depends(get_current_user),
    tips: TipService = Depends(get_tip_service),
):
    try:
        return await tips.list_reports(user["sub"], pending_only)
    except TipPermissionError:
        raise HTTPException(status_code=403, detail="Требуется роль редактора")


@router.post("/moderation/reports/{report_id}/resolve")
async def resolve_tip_report(
    report_id: str, payload: TipReportResolutionIn, user: dict = Depends(get_current_user),
    tips: TipService = Depends(get_tip_service),
):
    try:
        return await tips.resolve_report(user["sub"], report_id, payload.resolution, payload.note)
    except TipPermissionError:
        raise HTTPException(status_code=403, detail="Требуется роль редактора")
    except TipNotFoundError:
        raise HTTPException(status_code=404, detail="Жалоба не найдена")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.get("/moderation/audit")
async def get_tip_audit(
    limit: int = Query(default=100, ge=1, le=200),
    user: dict = Depends(get_current_user),
    tips: TipService = Depends(get_tip_service),
):
    try:
        return await tips.list_audit(user["sub"], limit)
    except TipPermissionError:
        raise HTTPException(status_code=403, detail="Требуется роль редактора")
