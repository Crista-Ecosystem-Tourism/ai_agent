"""Account-owned interface preference API contracts."""

import unittest
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


class UserPreferencesApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_preferences_are_read_and_written_for_authenticated_account(self):
        users = FakeUserService()
        saved = await set_preferences(
            UserPreferencesIn(theme="light", language="en"), {"sub": "user-1"}, users
        )
        self.assertEqual(saved.model_dump(), {"theme": "light", "language": "en"})
        loaded = await get_preferences({"sub": "user-1"}, users)
        self.assertEqual(loaded, saved)

    async def test_preferences_do_not_return_another_or_missing_user(self):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as error:
            await get_preferences({"sub": "unknown"}, FakeUserService())
        self.assertEqual(error.exception.status_code, 404)

    def test_preferences_reject_unsupported_values(self):
        for payload in (
            {"theme": "system", "language": "ru"},
            {"theme": "dark", "language": "fr"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                UserPreferencesIn(**payload)
