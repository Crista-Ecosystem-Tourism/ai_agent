"""Small, dependency-free primitives for privacy-safe social invite tokens."""

import hashlib


def hash_invite_code(code: str) -> str:
    """Return a one-way digest suitable for persistence instead of the secret."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def canonical_friend_pair(first_user_id: str, second_user_id: str) -> tuple[str, str]:
    """Represent a symmetric friendship in one stable, database-safe order."""
    if not first_user_id or not second_user_id or first_user_id == second_user_id:
        raise ValueError("A friendship requires two different users")
    return tuple(sorted((first_user_id, second_user_id)))
