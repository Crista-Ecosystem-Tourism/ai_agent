import hmac, os, hashlib


SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "dev-session-key").encode()

def hash_secret(secret: str) -> bytes:
    return hmac.new(SESSION_SECRET_KEY, secret.encode("utf-8"), hashlib.sha256).digest()

def verify_secret(stored_hash: bytes | None, provided_secret: str | None) -> bool:
    if not stored_hash or not provided_secret:
        return False
    test = hash_secret(provided_secret)
    return hmac.compare_digest(stored_hash, test)
