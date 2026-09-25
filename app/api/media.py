from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import Response as BinaryResponse

from app.dependencies import get_media_service
from app.security.deps import get_current_user
from app.services.media import (
    MediaLimitError,
    MediaNotFoundError,
    MediaService,
    MediaStorageUnavailable,
)
from app.core.media_policy import MAX_UPLOAD_BYTES, MediaProcessingUnavailable, MediaValidationError


router = APIRouter(prefix="/media", tags=["media"])


@router.get("/mine")
async def list_my_media(
    user: dict = Depends(get_current_user), media: MediaService = Depends(get_media_service),
):
    return await media.list_mine(user["sub"])


@router.post("", status_code=201)
async def upload_media(
    quest_id: str = Query(min_length=1, max_length=160),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    media: MediaService = Depends(get_media_service),
):
    chunks = bytearray()
    try:
        while chunk := await file.read(1024 * 1024):
            chunks.extend(chunk)
            if len(chunks) > MAX_UPLOAD_BYTES:
                raise MediaValidationError("Максимальный размер файла — 50 МБ")
        return await media.upload(user["sub"], quest_id, bytes(chunks))
    except MediaValidationError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except MediaNotFoundError as error:
        raise HTTPException(status_code=404, detail="Квест или файл не найден") from error
    except MediaLimitError as error:
        raise HTTPException(status_code=429, detail="Лимит медиатеки: 100 снимков и 250 МБ на аккаунт") from error
    except MediaStorageUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except MediaProcessingUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    finally:
        await file.close()


@router.get("/{asset_id}/preview")
async def get_media_preview(
    asset_id: str, user: dict = Depends(get_current_user), media: MediaService = Depends(get_media_service),
):
    try:
        data = await media.read_mine(user["sub"], asset_id, preview=True)
    except MediaNotFoundError as error:
        raise HTTPException(status_code=404, detail="Файл не найден") from error
    except MediaStorageUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return BinaryResponse(data, media_type="image/jpeg", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/{asset_id}/file")
async def get_media_file(
    asset_id: str, user: dict = Depends(get_current_user), media: MediaService = Depends(get_media_service),
):
    try:
        data, content_type = await media.read_mine_with_type(user["sub"], asset_id)
    except MediaNotFoundError as error:
        raise HTTPException(status_code=404, detail="Файл не найден") from error
    except MediaStorageUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return BinaryResponse(data, media_type=content_type, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.delete("/{asset_id}", status_code=204)
async def delete_media(
    asset_id: str, user: dict = Depends(get_current_user), media: MediaService = Depends(get_media_service),
):
    try:
        await media.delete_mine(user["sub"], asset_id)
    except MediaNotFoundError as error:
        raise HTTPException(status_code=404, detail="Файл не найден") from error
    return Response(status_code=204)
