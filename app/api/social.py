"""Authenticated friend invitations and accepted friendship management."""

from typing import Literal

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
    SocialSharedQuestExistsError,
    SocialSharedQuestTeamTooSmallError,
    SocialSharedQuestUnavailableError,
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


class CreateSharedQuestIn(BaseModel):
    quest_id: str = Field(min_length=1, max_length=160)


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


@router.get("/league")
async def get_weekly_league(
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    return await social.get_weekly_league(user["sub"])


@router.post("/league/join")
async def join_weekly_league(
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    return await social.join_weekly_league(user["sub"])


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


@router.get("/team-quest-catalog")
async def list_shared_quest_catalog(
    language: Literal["ru", "en"] = "ru",
    _user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    return await social.list_shared_quest_catalog(language)


@router.get("/teams/{team_id}/quests")
async def list_shared_quests(
    team_id: str,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        return await social.list_shared_quests(user["sub"], team_id, language)
    except SocialTeamNotFoundError:
        raise HTTPException(status_code=404, detail="Команда недоступна")


@router.post("/teams/{team_id}/quests", status_code=status.HTTP_201_CREATED)
async def create_shared_quest(
    team_id: str,
    payload: CreateSharedQuestIn,
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        return await social.create_shared_quest(user["sub"], team_id, payload.quest_id)
    except SocialTeamPermissionError:
        raise HTTPException(status_code=403, detail="Только владелец или админ может запустить квест")
    except SocialSharedQuestTeamTooSmallError:
        raise HTTPException(status_code=409, detail="Для совместного квеста нужны минимум два участника")
    except SocialSharedQuestExistsError:
        raise HTTPException(status_code=409, detail="Эта команда уже запускала данный квест")
    except SocialSharedQuestUnavailableError:
        raise HTTPException(status_code=404, detail="Опубликованный квест недоступен")
    except SocialTeamNotFoundError:
        raise HTTPException(status_code=404, detail="Команда недоступна")


@router.post("/teams/{team_id}/quests/{shared_quest_id}/claim")
async def claim_shared_quest(
    team_id: str,
    shared_quest_id: str,
    language: Literal["ru", "en"] = "ru",
    user: dict = Depends(get_current_user),
    social: SocialService = Depends(get_social_service),
):
    try:
        return await social.claim_shared_quest(user["sub"], team_id, shared_quest_id, language)
    except SocialTeamPermissionError:
        raise HTTPException(status_code=403, detail="Награду может получить только участник совместного квеста")
    except SocialTeamNotFoundError:
        raise HTTPException(status_code=404, detail="Совместный квест недоступен")
