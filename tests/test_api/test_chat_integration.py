"""Интеграционные тесты API — endpoint /chat/sessions/{id}/messages."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.services.processor import ProcessorResult
from app.api.schemas import SearchResult, Place


def _make_test_app():
    """Создать минимальное FastAPI-приложение для тестирования chat router."""
    from fastapi import FastAPI
    from app.api.chat import router

    app = FastAPI()
    app.include_router(router)
    return app


def _mock_processor_result_with_route(sample_places, mock_geojson):
    """Создать ProcessorResult с маршрутом."""
    structured = [
        SearchResult(
            query="достопримечательности Москва",
            places=sample_places,
            count=len(sample_places),
        )
    ]
    return ProcessorResult(
        response=structured,
        has_results=True,
        is_complete=False,
        route_geojson=mock_geojson,
        route_metadata={
            "graph_id": "test-123",
            "build_time_seconds": 1.0,
            "nodes_count": 3,
            "edges_count": 2,
            "alternatives_count": 1,
            "metrics": {},
        },
    )


# ---------------------------------------------------------------------------
# 1. Полный pipeline через TestClient (мок processor)
# ---------------------------------------------------------------------------

def test_send_message_returns_route_geojson():
    """POST /chat/sessions/{id}/messages возвращает route_geojson в ответе."""
    sample_places = [
        Place(id="1", name="Красная площадь", latitude=55.75, longitude=37.62, rating=4.8),
        Place(id="2", name="Третьяковка", latitude=55.74, longitude=37.62, rating=4.7),
    ]
    mock_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [37.62, 55.75]},
                "properties": {"name": "Красная площадь"},
            }
        ],
    }

    processor_result = _mock_processor_result_with_route(sample_places, mock_geojson)

    # Мок всех зависимостей
    mock_processor = AsyncMock()
    mock_processor.process_message = AsyncMock(return_value=processor_result)

    mock_chat_srv = AsyncMock()
    mock_chat_srv.get_owner = AsyncMock(return_value=None)
    mock_chat_srv.verify_anonymous_access = AsyncMock(return_value=True)
    mock_chat_srv.touch = AsyncMock()

    mock_history_srv = AsyncMock()
    mock_history_srv.load_for_context = AsyncMock(return_value=[])
    mock_history_srv.append_messages = AsyncMock()

    mock_http_client = AsyncMock()

    app = _make_test_app()

    # Перекрываем зависимости
    from app.dependencies import (
        get_message_processor,
        get_chat_session_service,
        get_history_service,
        get_http_client,
    )
    from app.security.deps import get_optional_user

    app.dependency_overrides[get_message_processor] = lambda: mock_processor
    app.dependency_overrides[get_chat_session_service] = lambda: mock_chat_srv
    app.dependency_overrides[get_history_service] = lambda: mock_history_srv
    app.dependency_overrides[get_http_client] = lambda: mock_http_client
    app.dependency_overrides[get_optional_user] = lambda: None

    with TestClient(app) as client:
        resp = client.post(
            "/chat/sessions/test-session-id/messages",
            json={
                "message": "Покажи достопримечательности Москвы",
                "session_secret": "test-secret",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["has_search_results"] is True
    assert body["route_geojson"] is not None
    assert body["route_geojson"]["type"] == "FeatureCollection"
    assert body["route_metadata"] is not None
    assert body["route_metadata"]["graph_id"] == "test-123"


# ---------------------------------------------------------------------------
# 2. Ответ без маршрута (graceful degradation)
# ---------------------------------------------------------------------------

def test_send_message_without_route():
    """Когда маршрут недоступен, route_geojson = null, но ответ корректен."""
    processor_result = ProcessorResult(
        response="Куда вы хотите поехать?",
        has_results=False,
        is_complete=False,
        route_geojson=None,
        route_metadata=None,
    )

    mock_processor = AsyncMock()
    mock_processor.process_message = AsyncMock(return_value=processor_result)

    mock_chat_srv = AsyncMock()
    mock_chat_srv.get_owner = AsyncMock(return_value=None)
    mock_chat_srv.verify_anonymous_access = AsyncMock(return_value=True)
    mock_chat_srv.touch = AsyncMock()

    mock_history_srv = AsyncMock()
    mock_history_srv.load_for_context = AsyncMock(return_value=[])
    mock_history_srv.append_messages = AsyncMock()

    mock_http_client = AsyncMock()

    app = _make_test_app()

    from app.dependencies import (
        get_message_processor,
        get_chat_session_service,
        get_history_service,
        get_http_client,
    )
    from app.security.deps import get_optional_user

    app.dependency_overrides[get_message_processor] = lambda: mock_processor
    app.dependency_overrides[get_chat_session_service] = lambda: mock_chat_srv
    app.dependency_overrides[get_history_service] = lambda: mock_history_srv
    app.dependency_overrides[get_http_client] = lambda: mock_http_client
    app.dependency_overrides[get_optional_user] = lambda: None

    with TestClient(app) as client:
        resp = client.post(
            "/chat/sessions/test-session-id/messages",
            json={
                "message": "Привет",
                "session_secret": "test-secret",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["route_geojson"] is None
    assert body["route_metadata"] is None
    assert body["message"] == "Куда вы хотите поехать?"
