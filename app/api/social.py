"""Authenticated friend invitations and accepted friendship management."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.dependencies import get_social_service
from app.security.deps import get_current_user
from app.services.social import (
    SocialInviteLimitError,
    SocialInviteNotFoundError,
    SocialTeamLimitError,
    SocialTeamNotFoundError,
    SocialTeamPermissionError,
    SocialService,
)


router = APIRouter(prefix="/social", tags=["social"])


class AcceptFriendInviteIn(BaseModel):
    invite_code: str = Field(min_length=32, max_length=128)


class CreateTeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AddTeamMemberIn(BaseModel):
    friend_id: str = Field(min_length=1, max_length=160)


class UpdateTeamRoleIn(BaseModel):
    role: str = Field(pattern="^(admin|member)$")


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


@router.get("/teams")
async def list_teams(
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    return await social.list_teams(user["sub"])


@router.post("/teams", status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: CreateTeamIn,
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        return await social.create_team(user["sub"], payload.name)
    except SocialTeamLimitError:
        raise HTTPException(status_code=429, detail="Достигнут лимит команд")
    except SocialTeamNotFoundError:
        raise HTTPException(status_code=404, detail="Команда недоступна")
    except ValueError:
        raise HTTPException(status_code=422, detail="Название команды недопустимо")


@router.post("/teams/{team_id}/members", status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: str,
    payload: AddTeamMemberIn,
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        created = await social.add_team_member(user["sub"], team_id, payload.friend_id)
        return {"created": created}
    except SocialTeamPermissionError:
        raise HTTPException(status_code=403, detail="Недостаточно прав для изменения команды")
    except SocialTeamNotFoundError:
        raise HTTPException(status_code=404, detail="Команда или друг недоступны")
    except SocialTeamLimitError:
        raise HTTPException(status_code=429, detail="Достигнут лимит участников команды")


@router.patch("/teams/{team_id}/members/{member_id}")
async def change_team_role(
    team_id: str,
    member_id: str,
    payload: UpdateTeamRoleIn,
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        return {"changed": await social.change_team_role(user["sub"], team_id, member_id, payload.role)}
    except SocialTeamPermissionError:
        raise HTTPException(status_code=403, detail="Только владелец может назначать роли")
    except SocialTeamNotFoundError:
        raise HTTPException(status_code=404, detail="Участник команды недоступен")


@router.delete("/teams/{team_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: str,
    member_id: str,
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        await social.remove_team_member(user["sub"], team_id, member_id)
    except SocialTeamPermissionError:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления участника")
    except SocialTeamNotFoundError:
        raise HTTPException(status_code=404, detail="Участник команды недоступен")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
