from typing import Literal

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


class MiniSiteStampTicketIn(BaseModel):
    stamp_keys: list[str] = Field(min_length=1, max_length=20)


class BossAnswerItem(BaseModel):
    question_id: str = Field(min_length=1, max_length=120)
    answer_key: str = Field(min_length=1, max_length=80)


class MoscowBossAnswerIn(BaseModel):
    answers: list[BossAnswerItem] = Field(min_length=3, max_length=3)


class TruthMythAnswerIn(BaseModel):
    statement_id: str = Field(min_length=1, max_length=120)
    answer_key: str = Field(pattern="^(truth|myth)$")


class MatchingAnswerItem(BaseModel):
    pair_id: str = Field(min_length=1, max_length=120)
    choice_id: str = Field(min_length=1, max_length=120)


class MoscowMatchingAnswerIn(BaseModel):
    answers: list[MatchingAnswerItem] = Field(min_length=3, max_length=3)


class MoscowTimelineAnswerIn(BaseModel):
    ordered_ids: list[str] = Field(min_length=3, max_length=3)


class MoscowWordBlocksAnswerIn(BaseModel):
    ordered_ids: list[str] = Field(min_length=4, max_length=4)


class MoscowPriceSliderAnswerIn(BaseModel):
    value: int = Field(ge=0, le=10000)


class MoscowPhotoScannerAnswerIn(BaseModel):
    hotspot_id: str = Field(min_length=1, max_length=120)


@router.get("/passport")
async def get_passport(
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    return await game.get_passport(user["sub"])


@router.post("/passport/mini-site-ticket")
async def create_mini_site_stamp_ticket(
    payload: MiniSiteStampTicketIn,
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.create_mini_site_stamp_ticket(user["sub"], payload.stamp_keys)
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Выбранные игровые штампы недоступны")


@router.get("/onboarding")
async def get_onboarding(
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_onboarding(user["sub"], language)
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
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_moscow_quest(user["sub"], quest_id, language)
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
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_quest(user["sub"], quest_id, payload.answer_key, language)
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


@router.get("/paths/{city_id}")
async def get_city_path(
    city_id: str,
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_city_path(user["sub"], city_id)
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Маршрут города временно недоступен",
        )


@router.get("/paths/{city_id}/quests/{quest_id}")
async def get_city_quest(
    city_id: str,
    quest_id: str,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_city_quest(user["sub"], city_id, quest_id, language)
    except GameQuestLockedError:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Сначала заверши предыдущий квест")
    except GameContentUnavailableError:
        raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail="Квест города временно недоступен")


@router.post("/paths/{city_id}/quests/{quest_id}/answer")
async def answer_city_quest(
    city_id: str,
    quest_id: str,
    payload: RedSquareAnswerIn,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_city_quest(user["sub"], city_id, quest_id, payload.answer_key, language)
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Неизвестный вариант ответа")
    except GameQuestLockedError:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Сначала заверши предыдущий квест")
    except GameContentUnavailableError:
        raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail="Квест города временно недоступен")


@router.get("/paths/moscow/boss")
async def get_moscow_boss(
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_moscow_boss(user["sub"], language)
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


@router.get("/paths/moscow/sandbox")
async def get_moscow_sandbox(
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.get_moscow_sandbox(user["sub"], language)
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши финальный круг Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Песочница Москвы временно недоступна",
        )


@router.post("/paths/moscow/sandbox/truth-myth/answer")
async def answer_moscow_truth_myth(
    payload: TruthMythAnswerIn,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_truth_myth(
            user["sub"], payload.statement_id, payload.answer_key, language,
        )
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Неизвестный ответ для упражнения")
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши финальный круг Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Упражнение «Правда или миф» временно недоступно",
        )


@router.post("/paths/moscow/sandbox/matching/answer")
async def answer_moscow_matching(
    payload: MoscowMatchingAnswerIn,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_matching(
            user["sub"], [answer.model_dump() for answer in payload.answers], language,
        )
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Нужно сопоставить все три карточки")
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши финальный круг Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Упражнение на сопоставление временно недоступно",
        )


@router.post("/paths/moscow/sandbox/timeline/answer")
async def answer_moscow_timeline(
    payload: MoscowTimelineAnswerIn,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_timeline(user["sub"], payload.ordered_ids, language)
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Нужно расставить все три события")
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши финальный круг Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Упражнение на хронологию временно недоступно",
        )


@router.post("/paths/moscow/sandbox/word-blocks/answer")
async def answer_moscow_word_blocks(
    payload: MoscowWordBlocksAnswerIn,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_word_blocks(user["sub"], payload.ordered_ids, language)
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Нужно собрать все четыре слова")
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши финальный круг Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Упражнение со словами временно недоступно",
        )


@router.post("/paths/moscow/sandbox/price-slider/answer")
async def answer_moscow_price_slider(
    payload: MoscowPriceSliderAnswerIn,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_price_slider(user["sub"], payload.value, language)
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Значение вне диапазона упражнения")
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши финальный круг Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Упражнение с ценой временно недоступно",
        )


@router.post("/paths/moscow/sandbox/restore-energy")
async def restore_moscow_energy(
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.restore_moscow_energy_from_practice(user["sub"])
    except ValueError as error:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(error))
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши финальный круг Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Песочница Москвы временно недоступна",
        )


@router.post("/paths/moscow/sandbox/photo-scanner/answer")
async def answer_moscow_photo_scanner(
    payload: MoscowPhotoScannerAnswerIn,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_photo_scanner(user["sub"], payload.hotspot_id, language)
    except ValueError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Неизвестная область фотографии")
    except GameQuestLockedError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Сначала заверши финальный круг Москвы",
        )
    except GameContentUnavailableError:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Фото-сканер временно недоступен",
        )


@router.post("/paths/moscow/boss/answer")
async def answer_moscow_boss(
    payload: MoscowBossAnswerIn,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    game: GameProgressService = Depends(get_game_progress_service),
):
    try:
        return await game.answer_moscow_boss(
            user["sub"], [answer.model_dump() for answer in payload.answers], language,
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
