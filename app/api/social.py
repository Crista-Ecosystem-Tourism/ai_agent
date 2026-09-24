"""Authenticated friend invitations and accepted friendship management."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.dependencies import get_social_service
from app.security.deps import get_current_user
from app.services.social import (
    SocialInviteLimitError,
    SocialInviteNotFoundError,
    SocialService,
)


router = APIRouter(prefix="/social", tags=["social"])


class AcceptFriendInviteIn(BaseModel):
    invite_code: str = Field(min_length=32, max_length=128)


@router.post("/invites", status_code=status.HTTP_201_CREATED)
async def create_friend_invite(
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        return await social.create_friend_invite(user["sub"])
    except SocialInviteLimitError:
        raise HTTPException(status_code=429, detail="Слишком много активных приглашений")
    except SocialInviteNotFoundError:
        raise HTTPException(status_code=404, detail="Приглашение недоступно")


@router.post("/invites/accept")
async def accept_friend_invite(
    payload: AcceptFriendInviteIn,
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        return await social.accept_friend_invite(user["sub"], payload.invite_code)
    except SocialInviteNotFoundError:
        raise HTTPException(status_code=404, detail="Приглашение недоступно")


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_friend_invite(
    invite_id: str,
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        await social.revoke_friend_invite(user["sub"], invite_id)
    except SocialInviteNotFoundError:
        raise HTTPException(status_code=404, detail="Приглашение недоступно")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/friends")
async def list_friends(
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    return await social.list_friends(user["sub"])


@router.delete("/friends/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friend(
    friend_id: str,
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        await social.remove_friend(user["sub"], friend_id)
    except SocialInviteNotFoundError:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)
