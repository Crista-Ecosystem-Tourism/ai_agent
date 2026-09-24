"""Account-owned interface preference API contracts."""

import pytest
from pydantic import ValidationError

from app.api.auth import UserPreferencesIn, get_preferences, set_preferences


class FakeUserService:
    def __init__(self):
        self.preferences = {"theme": "dark", "language": "ru"}

    async def get_preferences(self, user_id):
        return self.preferences if user_id == "user-1" else None

    async def set_preferences(self, user_id, theme, language):
        if user_id != "user-1":
            return None
        self.preferences = {"theme": theme, "language": language}
        return self.preferences


@pytest.mark.asyncio
async def test_preferences_are_read_and_written_for_authenticated_account():
    users = FakeUserService()
    saved = await set_preferences(
        UserPreferencesIn(theme="light", language="en"), {"sub": "user-1"}, users
    )
    assert saved.model_dump() == {"theme": "light", "language": "en"}
    loaded = await get_preferences({"sub": "user-1"}, users)
    assert loaded == saved


@pytest.mark.asyncio
async def test_preferences_do_not_return_another_or_missing_user():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        await get_preferences({"sub": "unknown"}, FakeUserService())
    assert error.value.status_code == 404


@pytest.mark.parametrize("payload", [
    {"theme": "system", "language": "ru"},
    {"theme": "dark", "language": "fr"},
])
def test_preferences_reject_unsupported_values(payload):
    with pytest.raises(ValidationError):
        UserPreferencesIn(**payload)
