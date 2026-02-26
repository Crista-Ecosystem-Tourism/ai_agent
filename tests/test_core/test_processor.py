"""Тесты для MessageProcessor — интеграция с маршрутизацией."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import fields

from app.core.services.processor import MessageProcessor, ProcessorResult
from app.core.models import TravelDeps, UserPreferences
from app.api.schemas import SearchResult


def _make_deps(city="Москва", destination_type="город", activities=None):
    """Вспомогательный конструктор TravelDeps с заполненными предпочтениями."""
    prefs = UserPreferences(
        city=city,
        destination_type=destination_type,
        travel_companions="пара",
        budget="средний",
        activities=activities or ["достопримечательности"],
    )
    return TravelDeps(
        rag_service_url="http://localhost:8001/api/v1",
        http_client=AsyncMock(),
        user_preferences=prefs,
    )


def _make_processor():
    """Создать MessageProcessor с мок-агентом."""
    mock_agent = MagicMock()
    # _update_preferences вызывает preferences_agent.agent.run(...)
    mock_run_result = AsyncMock()
    mock_run_result.output = UserPreferences(
        city="Москва",
        destination_type="город",
        travel_companions="пара",
        budget="средний",
        activities=["достопримечательности"],
    )
    mock_agent.agent.run = AsyncMock(return_value=mock_run_result)
    return MessageProcessor(preferences_agent=mock_agent, model=MagicMock())


# ---------------------------------------------------------------------------
# 1. process_message с маршрутом
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route")
@patch("app.core.services.processor.PlacesSearchService.search_places_in_rag")
async def test_process_message_with_route(
    mock_search, mock_build_route, sample_places, mock_route_response
):
    """При наличии результатов поиска маршрут строится и возвращается."""
    mock_search.return_value = sample_places

    # Имитируем RouteResult
    from app.core.services.route import RouteResult
    mock_build_route.return_value = RouteResult(
        geojson=mock_route_response["geojson"],
        graph_id="test-graph-123",
        build_time_seconds=1.23,
        metrics=mock_route_response["metrics"],
        nodes_count=3,
        edges_count=2,
        alternatives_count=1,
    )

    processor = _make_processor()
    deps = _make_deps()

    result = await processor.process_message("Покажи достопримечательности Москвы", deps)

    assert isinstance(result, ProcessorResult)
    assert result.has_results is True
    assert result.route_geojson is not None
    assert result.route_geojson["type"] == "FeatureCollection"
    assert result.route_metadata is not None
    assert result.route_metadata["graph_id"] == "test-graph-123"
    mock_build_route.assert_called_once()


# ---------------------------------------------------------------------------
# 2. process_message при недоступности маршрутизации
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route")
@patch("app.core.services.processor.PlacesSearchService.search_places_in_rag")
async def test_process_message_route_unavailable(
    mock_search, mock_build_route, sample_places
):
    """При ошибке маршрутизации результаты поиска всё равно возвращаются."""
    mock_search.return_value = sample_places
    mock_build_route.return_value = None  # маршрутизация недоступна

    processor = _make_processor()
    deps = _make_deps()

    result = await processor.process_message("Покажи достопримечательности Москвы", deps)

    assert isinstance(result, ProcessorResult)
    assert result.has_results is True
    assert result.route_geojson is None
    assert result.route_metadata is None
    # Поисковые результаты есть
    assert isinstance(result.response, list)


# ---------------------------------------------------------------------------
# 3. process_message при недостаточной информации (без маршрута)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_message_insufficient_info():
    """Если предпочтений недостаточно, маршрут не строится."""
    mock_agent = MagicMock()
    # Возвращаем пустые предпочтения → has_searchable_info() == False
    mock_run_result = AsyncMock()
    mock_run_result.output = UserPreferences()
    mock_agent.agent.run = AsyncMock(return_value=mock_run_result)

    # Мок для follow_up Agent
    with patch("app.core.services.processor.Agent") as MockAgent:
        mock_follow_up_result = AsyncMock()
        mock_follow_up_result.output = "Куда вы хотите поехать?"
        MockAgent.return_value.run = AsyncMock(return_value=mock_follow_up_result)

        processor = MessageProcessor(preferences_agent=mock_agent, model=MagicMock())
        deps = TravelDeps(
            rag_service_url="http://localhost:8001/api/v1",
            http_client=AsyncMock(),
            user_preferences=UserPreferences(),
        )

        result = await processor.process_message("Привет", deps)

    assert isinstance(result, ProcessorResult)
    assert result.has_results is False
    assert result.route_geojson is None
    assert result.route_metadata is None
    assert isinstance(result.response, str)


# ---------------------------------------------------------------------------
# 4. ProcessorResult содержит все поля
# ---------------------------------------------------------------------------

def test_processor_result_has_all_fields():
    """ProcessorResult содержит обязательные поля для API-ответа."""
    field_names = {f.name for f in fields(ProcessorResult)}
    expected = {
        "response", "has_results", "is_complete",
        "route_geojson", "route_metadata",
        "search_results", "itinerary", "suggested_replies",
    }
    assert expected == field_names
