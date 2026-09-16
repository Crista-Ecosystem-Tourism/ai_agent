from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_503_SERVICE_UNAVAILABLE

from app.dependencies import get_game_progress_service
from app.security.deps import get_current_user
from app.services.game_progress import GameContentUnavailableError, GameProgressService


router = APIRouter(prefix="/game", tags=["game"])


class RedSquareAnswerIn(BaseModel):
    answer_key: str = Field(min_length=1, max_length=80)


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
