import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT

from app.security.jwt import create_access_token
from app.security.password import hash_password, verify_password
from app.security.deps import get_current_user
from app.services.user import UserService
from app.dependencies import get_user_service


router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# ---------- schemas ----------

class RegisterIn(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError("Некорректный адрес электронной почты")
        return v.lower()


class LoginIn(BaseModel):
    email: str = Field(..., description="User email")
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError("Некорректный адрес электронной почты")
        return v.lower()


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None


class AuthOut(BaseModel):
    access_token: str
    user: UserOut


# ---------- endpoints ----------

@router.post("/register", response_model=AuthOut)
async def register(
    payload: RegisterIn,
    user_service: UserService = Depends(get_user_service),
):
    existing = await user_service.get_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует",
        )

    hashed = hash_password(payload.password)
    user = await user_service.create_with_password(
        email=payload.email,
        name=payload.name,
        hashed_password=hashed,
    )

    token = create_access_token(sub=user.id, extra={"email": user.email})
    return AuthOut(
        access_token=token,
        user=UserOut(id=user.id, email=user.email, name=user.name),
    )


@router.post("/login", response_model=AuthOut)
async def login(
    payload: LoginIn,
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.get_by_email(payload.email)
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Аккаунт деактивирован",
        )

    token = create_access_token(sub=user.id, extra={"email": user.email})
    return AuthOut(
        access_token=token,
        user=UserOut(id=user.id, email=user.email, name=user.name),
    )


@router.get("/me", response_model=UserOut)
async def me(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    user_data = await user_service.get_by_id(current_user["sub"])
    if not user_data:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return UserOut(
        id=user_data["id"],
        email=user_data["email"],
        name=user_data["name"],
    )
