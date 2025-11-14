import time
import httpx
import jwt

from typing import Optional, Dict, Any


GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_JWKS: Optional[Dict[str, Any]] = None
_GOOGLE_JWKS_TS: float = 0
_JWKS_TTL = 3600

async def _get_google_jwks() -> Dict[str, Any]:
    global _GOOGLE_JWKS, _GOOGLE_JWKS_TS
    now = time.time()
    if _GOOGLE_JWKS and now - _GOOGLE_JWKS_TS < _JWKS_TTL:
        return _GOOGLE_JWKS
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(GOOGLE_JWKS_URL)
        r.raise_for_status()
        _GOOGLE_JWKS = r.json()
        _GOOGLE_JWKS_TS = now
        return _GOOGLE_JWKS

def _find_key(jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, Any]]:
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            return k
    return None

async def validate_google_id_token(id_token: str, audience: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        unverified = jwt.get_unverified_header(id_token)
        kid = unverified.get("kid")
        if not kid:
            return None
        jwks = await _get_google_jwks()
        key = _find_key(jwks, kid)
        if not key:
            return None
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        payload = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=audience,  # ваш GOOGLE_CLIENT_ID, можно None для пропуска проверки
            options={"verify_aud": audience is not None}
        )
        if payload.get("iss") not in GOOGLE_ISSUERS:
            return None
        return payload
    except Exception:
        return None
