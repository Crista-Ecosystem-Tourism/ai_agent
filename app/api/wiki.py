import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from app.dependencies import get_wiki_service
from app.security.deps import get_current_user
from app.services.wiki import WikiNotFoundError, WikiService


router = APIRouter(prefix="/wiki", tags=["wiki"])
SLUG_RE = re.compile(r"^[a-z0-9-]{2,80}$")


class WikiSourceIn(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=8, max_length=2048)


class WikiDraftIn(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    body: dict[str, Any]
    sources: list[WikiSourceIn] = Field(min_length=1, max_length=50)
    license: str = Field(min_length=1, max_length=160)


@router.get("/drafts/mine")
async def get_my_wiki_drafts(
    user: dict = Depends(get_current_user),
    wiki: WikiService = Depends(get_wiki_service),
):
    return await wiki.list_authored(user["sub"])


@router.get("/articles/{slug}")
async def get_wiki_article(
    slug: str,
    language: Literal["ru", "en"] = "ru",
    wiki: WikiService = Depends(get_wiki_service),
):
    try:
        return await wiki.get_published(slug, language)
    except WikiNotFoundError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Опубликованная статья не найдена")


@router.get("/versions/{version_id}")
async def get_wiki_version(version_id: str, wiki: WikiService = Depends(get_wiki_service)):
    try:
        return await wiki.get_published_version(version_id)
    except WikiNotFoundError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Опубликованная версия не найдена")


@router.post("/drafts")
async def create_wiki_draft(
    payload: WikiDraftIn,
    user: dict = Depends(get_current_user),
    wiki: WikiService = Depends(get_wiki_service),
):
    if not SLUG_RE.fullmatch(payload.slug):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Slug должен состоять из строчных латинских букв, цифр и дефисов")
    return await wiki.create_draft(
        user["sub"], payload.slug, payload.title, payload.body,
        [source.model_dump() for source in payload.sources], payload.license,
    )


@router.post("/drafts/{version_id}/submit")
async def submit_wiki_draft(
    version_id: str,
    user: dict = Depends(get_current_user),
    wiki: WikiService = Depends(get_wiki_service),
):
    try:
        return await wiki.submit_for_review(user["sub"], version_id)
    except WikiNotFoundError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Черновик не найден")
    except ValueError as error:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(error))


@router.post("/review/{version_id}/publish")
async def publish_wiki_version(
    version_id: str,
    user: dict = Depends(get_current_user),
    wiki: WikiService = Depends(get_wiki_service),
):
    try:
        return await wiki.publish_reviewed(user["sub"], version_id)
    except PermissionError as error:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=str(error))
    except WikiNotFoundError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Версия не найдена")
    except ValueError as error:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/review")
async def get_wiki_review_queue(
    user: dict = Depends(get_current_user),
    wiki: WikiService = Depends(get_wiki_service),
):
    try:
        return await wiki.list_review_queue(user["sub"])
    except PermissionError as error:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=str(error))
