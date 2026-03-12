from typing import Optional, Dict, Any# ваш HS256
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from app.security.jwt import decode_token as decode_first_party  
from app.security.token_validation import validate_google_id_token


bearer = HTTPBearer(auto_error=True)

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        payload = decode_first_party(creds.credentials)
        return payload
    except Exception:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен"
        )

async def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[Dict[str, Any]]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()

    payload = await validate_google_id_token(token, audience=None)  # или audience=GOOGLE_CLIENT_ID
    if payload:
        return {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "iss": payload.get("iss"),
            "provider": "google"
        }
    
    try:
        payload = decode_first_party(token)
        return {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "provider": "first_party"
        }
    except Exception:
        pass
    
    return None
