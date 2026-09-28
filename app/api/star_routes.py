from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_503_SERVICE_UNAVAILABLE

from app.dependencies import get_star_route_service
from app.security.deps import get_current_user
from app.services.star_routes import StarRouteNotFoundError, StarRouteRoutingUnavailable, StarRouteService, StarRouteValidationError


router = APIRouter(prefix="/star-routes", tags=["star-routes"])


class TranscriptCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_url: str = Field(min_length=8, max_length=2048)
    author_name: str | None = Field(default=None, max_length=160)
    rights_basis: Literal["owned", "licensed", "written_permission"]


class TranscriptSegmentIn(BaseModel):
    start_seconds: int = Field(ge=0, le=172_800)
    end_seconds: int = Field(ge=1, le=172_800)
    excerpt: str = Field(min_length=1, max_length=2000)
    extracted_place_name: str = Field(min_length=1, max_length=200)


class CandidatePoiIn(BaseModel):
    segment_id: str = Field(min_length=1, max_length=64)
    poi_id: str | None = Field(default=None, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source_url: str = Field(min_length=8, max_length=2048)


class CandidateCreateIn(BaseModel):
    transcript_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    pois: list[CandidatePoiIn] = Field(min_length=2, max_length=20)


def _service_error(error: Exception) -> HTTPException:
    if isinstance(error, PermissionError):
        return HTTPException(status_code=HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, StarRouteNotFoundError):
        return HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Запись звёздного маршрута не найдена")
    if isinstance(error, StarRouteValidationError):
        return HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail="Маршрутный сервис временно недоступен")


@router.get("")
async def list_published_routes(service: StarRouteService = Depends(get_star_route_service)):
    return await service.list_published()


@router.post("/transcripts")
async def register_transcript(
    payload: TranscriptCreateIn,
    user: dict = Depends(get_current_user),
    service: StarRouteService = Depends(get_star_route_service),
):
    try:
        return await service.register_transcript(user["sub"], payload.model_dump())
    except (PermissionError, StarRouteNotFoundError, StarRouteValidationError) as error:
        raise _service_error(error)


@router.post("/transcripts/{transcript_id}/segments")
async def add_transcript_segment(
    transcript_id: str,
    payload: TranscriptSegmentIn,
    user: dict = Depends(get_current_user),
    service: StarRouteService = Depends(get_star_route_service),
):
    try:
        return await service.add_segment(user["sub"], transcript_id, payload.model_dump())
    except (PermissionError, StarRouteNotFoundError, StarRouteValidationError) as error:
        raise _service_error(error)


@router.post("/candidates")
async def create_candidate(
    payload: CandidateCreateIn,
    user: dict = Depends(get_current_user),
    service: StarRouteService = Depends(get_star_route_service),
):
    try:
        return await service.create_candidate(user["sub"], payload.model_dump())
    except (PermissionError, StarRouteNotFoundError, StarRouteValidationError, StarRouteRoutingUnavailable) as error:
        raise _service_error(error)


@router.get("/review")
async def list_review_queue(
    user: dict = Depends(get_current_user),
    service: StarRouteService = Depends(get_star_route_service),
):
    try:
        return await service.list_review_queue(user["sub"])
    except PermissionError as error:
        raise _service_error(error)


@router.post("/review/{candidate_id}/publish")
async def publish_candidate(
    candidate_id: str,
    user: dict = Depends(get_current_user),
    service: StarRouteService = Depends(get_star_route_service),
):
    try:
        return await service.publish_candidate(user["sub"], candidate_id)
    except (PermissionError, StarRouteNotFoundError, StarRouteValidationError) as error:
        raise _service_error(error)
