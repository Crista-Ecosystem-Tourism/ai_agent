from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT, HTTP_503_SERVICE_UNAVAILABLE

from app.dependencies import get_game_progress_service
from app.security.deps import get_current_user
from app.services.game_progress import (
    GameContentUnavailableError,
    GameProgressService,
    GameQuestLockedError,
)


router = APIRouter(prefix="/game", tags=["game"])


class RedSquareAnswerIn(BaseModel):
    answer_key: str = Field(min_length=1, max_length=80)


class BossAnswerItem(BaseModel):
    question_id: str = Field(min_length=1, max_length=120)
    answer_key: str = Field(min_length=1, max_length=80)


class MoscowBossAnswerIn(BaseModel):
    answers: list[BossAnswerItem] = Field(min_length=3, max_length=3)


@router.get("/onboarding")
async def get_onboarding(
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_onboarding(user["sub"])
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Игровой контент временно недоступен",
        )


@router.post("/onboarding/red-square/answer")
async def answer_red_square(
    payload: RedSquareAnswerIn,
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_red_square(user["sub"], payload.answer_key)
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Неизвестный вариант ответа")
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Игровой контент временно недоступен",
        )


@router.get("/paths/moscow")
async def get_moscow_path(
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_moscow_path(user["sub"])
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Маршрут Москвы временно недоступен",
        )


@router.get("/paths/moscow/quests/{quest_id}")
async def get_moscow_quest(
    quest_id: str,
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_moscow_quest(user["sub"], quest_id)
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши предыдущий квест Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Квест Москвы временно недоступен",
        )


@router.post("/paths/moscow/quests/{quest_id}/answer")
async def answer_moscow_quest(
    quest_id: str,
    payload: RedSquareAnswerIn,
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_quest(user["sub"], quest_id, payload.answer_key)
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Неизвестный вариант ответа")
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши предыдущий квест Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Квест Москвы временно недоступен",
        )


@router.get("/paths/moscow/boss")
async def get_moscow_boss(
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_moscow_boss(user["sub"])
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши все точки Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Финальный квест Москвы временно недоступен",
        )


@router.post("/paths/moscow/boss/answer")
async def answer_moscow_boss(
    payload: MoscowBossAnswerIn,
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_boss(
            user["sub"], [answer.model_dump() for answer in payload.answers],
        )
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Нужно ответить на все три вопроса")
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши все точки Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Финальный квест Москвы временно недоступен",
        )
