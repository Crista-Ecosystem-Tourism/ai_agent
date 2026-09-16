"""Access-control regression tests for anonymous chat sessions."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat import router
from app.dependencies import get_chat_session_service
from app.security.deps import get_optional_user
from app.security.session_secret import hash_secret
from app.services.chat_session import ChatSessionService


def _session_factory():
    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=db)
    return factory, db


@pytest.mark.asyncio
async def test_anonymous_access_rejects_claimed_and_expired_sessions():
    factory, db = _session_factory()
    service = ChatSessionService(factory)
    future = datetime.now(timezone.utc) + timedelta(minutes=5)

    db.execute.return_value = MagicMock(first=MagicMock(return_value=(False, None, future)))
    assert await service.verify_anonymous_access("session", "secret") is False

    expired = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.execute.return_value = MagicMock(
        first=MagicMock(return_value=(True, hash_secret("secret"), expired))
    )
    assert await service.verify_anonymous_access("session", "secret") is False


@pytest.mark.asyncio
async def test_claim_is_conditional_and_clears_the_anonymous_secret():
    factory, db = _session_factory()
    service = ChatSessionService(factory)
    stored_hash = hash_secret("correct-secret")
    select_result = MagicMock(first=MagicMock(return_value=(stored_hash,)))
    update_result = MagicMock(rowcount=1)
    db.execute.side_effect = [select_result, update_result]

    assert await service.claim_anonymous_session("session", "user-a", "correct-secret") is True
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_second_claimant_cannot_take_a_session_after_the_first_claim():
    factory, db = _session_factory()
    service = ChatSessionService(factory)
    stored_hash = hash_secret("correct-secret")
    db.execute.side_effect = [
        MagicMock(first=MagicMock(return_value=(stored_hash,))),
        MagicMock(rowcount=0),
    ]

    assert await service.claim_anonymous_session("session", "user-b", "correct-secret") is False
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


def _app(chat_service, user=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chat_session_service] = lambda: chat_service
    app.dependency_overrides[get_optional_user] = lambda: user
    return app


def test_attach_rejects_a_session_that_was_already_claimed():
    chat_service = AsyncMock()
    chat_service.claim_anonymous_session = AsyncMock(return_value=False)

    with TestClient(_app(chat_service, {"sub": "user-b"})) as client:
        response = client.post(
            "/chat/sessions/session-id/attach",
            json={"session_secret": "old-secret"},
        )

    assert response.status_code == 403
    chat_service.claim_anonymous_session.assert_awaited_once_with(
        "session-id", "user-b", "old-secret"
    )


def test_anonymous_title_update_requires_its_secret():
    chat_service = AsyncMock()
    chat_service.get_owner = AsyncMock(return_value=None)
    chat_service.verify_anonymous_access = AsyncMock(return_value=False)

    with TestClient(_app(chat_service)) as client:
        response = client.patch(
            "/chat/sessions/session-id",
            json={"title": "Новая тема"},
        )

    assert response.status_code == 403
    chat_service.update_title.assert_not_awaited()
