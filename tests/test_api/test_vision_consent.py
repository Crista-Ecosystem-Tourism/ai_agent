"""Contract tests for the photo-recognition consent boundary."""

import pytest

from app.api.vision import VisionConsentIn, get_vision_consent, set_vision_consent


class FakeUserService:
    def __init__(self):
        self.value = {"granted": False, "policy_version": None}

    async def get_vision_consent(self, user_id):
        return self.value if user_id == "user-1" else None

    async def set_vision_consent(self, user_id, granted, policy_version):
        if user_id != "user-1":
            return None
        self.value = {"granted": granted, "policy_version": policy_version}
        return self.value


@pytest.mark.asyncio
async def test_consent_is_server_owned_and_recognition_stays_unavailable():
    users = FakeUserService()
    changed = await set_vision_consent(
        VisionConsentIn(granted=True, policy_version="vision-v1"),
        {"sub": "user-1"},
        users,
    )
    assert changed.granted is True
    assert changed.recognition_available is False

    current = await get_vision_consent({"sub": "user-1"}, users)
    assert current.policy_version == "vision-v1"


def test_consent_rejects_unknown_policy_version():
    with pytest.raises(ValueError):
        VisionConsentIn(granted=True, policy_version="other")
