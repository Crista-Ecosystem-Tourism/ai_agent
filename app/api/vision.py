"""Explicit consent boundary for a future photo-recognition provider.

No image bytes are accepted here. Recognition must be wired only after a provider,
retention rules and human-confirmation flow are configured.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.status import HTTP_404_NOT_FOUND

from app.dependencies import get_user_service
from app.security.deps import get_current_user
from app.services.user import UserService


router = APIRouter(prefix="/vision", tags=["vision"])
VISION_POLICY_VERSION = "vision-v1"


class VisionConsentIn(BaseModel):
    granted: bool
    policy_version: Literal["vision-v1"]


class VisionConsentOut(BaseModel):
    granted: bool
    policy_version: str | None = None
    recognition_available: Literal[False] = False


@router.get("/consent", response_model=VisionConsentOut)
async def get_vision_consent(
    user: dict = Depends(get_current_user),
    users: UserService = Depends(get_user_service),
):
    consent = await users.get_vision_consent(user["sub"])
    if consent is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    return VisionConsentOut(**consent)


@router.put("/consent", response_model=VisionConsentOut)
async def set_vision_consent(
    payload: VisionConsentIn,
    user: dict = Depends(get_current_user),
    users: UserService = Depends(get_user_service),
):
    consent = await users.set_vision_consent(
        user["sub"], payload.granted, payload.policy_version
    )
    if consent is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    return VisionConsentOut(**consent)
