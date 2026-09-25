"""Small, dependency-free primitives for privacy-safe social invite tokens."""

import hashlib


TEAM_ROLES = frozenset({"owner", "admin", "member"})


def hash_invite_code(code: str) -> str:
    """Return a one-way digest suitable for persistence instead of the secret."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def canonical_friend_pair(first_user_id: str, second_user_id: str) -> tuple[str, str]:
    """Represent a symmetric friendship in one stable, database-safe order."""
    if not first_user_id or not second_user_id or first_user_id == second_user_id:
        raise ValueError("A friendship requires two different users")
    return tuple(sorted((first_user_id, second_user_id)))


def can_add_team_member(actor_role: str, requested_role: str) -> bool:
    """Only team managers may add a regular member; elevation is a separate owner action."""
    return actor_role in {"owner", "admin"} and requested_role == "member"


def can_change_team_role(actor_role: str, target_role: str, requested_role: str) -> bool:
    """The owner alone can change non-owner roles; ownership cannot be reassigned here."""
    return actor_role == "owner" and target_role in {"admin", "member"} and requested_role in {"admin", "member"}


def can_remove_team_member(actor_role: str, target_role: str, is_self: bool) -> bool:
    """Members may leave, owners cannot orphan a team, admins cannot remove admins."""
    if target_role == "owner":
        return False
    if is_self:
        return actor_role in TEAM_ROLES
    return actor_role == "owner" or (actor_role == "admin" and target_role == "member")


def shared_quest_reward_key(quest_id: str) -> str:
    """Return a stable user-scoped key so a quest bonus is earned only once globally."""
    if not quest_id:
        raise ValueError("A shared reward needs a stable quest ID")
    return f"team-quest:{quest_id}"
