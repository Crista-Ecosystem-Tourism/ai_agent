import os
import secrets

from typing import Optional
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, HTTPException, Depends

from app.dependencies import get_user_service
from app.security.jwt import create_access_token
from app.services.user import UserService


router = APIRouter(prefix="/auth/google", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

@router.get("/start")
async def google_login(request: Request):
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    redirect_uri = REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)

@router.get("/callback")
async def google_callback(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    try:
        state = request.query_params.get("state")
        code = request.query_params.get("code")
        
        session_state = request.session.get("oauth_state")
        if not session_state or not state or session_state != state:
            raise HTTPException(
                status_code=400, 
                detail="Ошибка авторизации Google: несовпадение состояния сессии (CSRF)"
            )
        
        request.session.pop("oauth_state", None)
        
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo") or {}
        
        email: Optional[str] = userinfo.get("email")
        sub: Optional[str] = userinfo.get("sub")
        name = userinfo.get("name")

        if not email or not sub:
            raise HTTPException(status_code=400, detail="Профиль Google не содержит email")

        user_id = await user_service.get_or_create_from_google(
            google_sub=sub,
            email=email,
            name=name
        )

        access = create_access_token(sub=user_id, extra={"email": email})
        
        return {"access_token": access, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка авторизации Google: {e}")


@router.get("/me")
async def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не авторизован")
    return user

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Вы вышли из системы"}

# Dev endpoint для тестирования
@router.get("/dev/token")
async def dev_token(email: str = "test@example.com"):
    from app.security.jwt import create_access_token
    user_id = f"dev_{email}"
    token = create_access_token(sub=user_id, extra={"email": email})
    return {
        "access_token": token, 
        "token_type": "bearer",
        "user": {"id": user_id, "email": email}
    }
