"""Тесты для MessageProcessor — интеграция с маршрутизацией."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import fields

from app.core.services.processor import MessageProcessor, ProcessorResult
from app.core.models import Itinerary, ItineraryDay, ItinerarySlot, TravelDeps, UserPreferences
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


def _make_itinerary() -> Itinerary:
    """Маршрут намеренно выбирает лишь часть найденных POI и задаёт их порядок."""
    return Itinerary(
        days=[
            ItineraryDay(
                day=1,
                title="Прогулка",
                slots=[
                    ItinerarySlot(time_label="Утро", place_id="2", place_name="Третьяковская галерея"),
                    ItinerarySlot(time_label="Вечер", place_id="3", place_name="Парк Горького"),
                ],
            )
        ],
        summary="Готово",
    )


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

    with patch.object(processor, "_generate_itinerary", new=AsyncMock(return_value=_make_itinerary())):
        result = await processor.process_message("Покажи достопримечательности Москвы", deps)

    assert isinstance(result, ProcessorResult)
    assert result.has_results is True
    assert result.route_geojson is not None
    assert result.route_geojson["type"] == "FeatureCollection"
    assert result.route_metadata is not None
    assert result.route_metadata["graph_id"] == "test-graph-123"
    assert result.itinerary.schema_version == 1
    mock_build_route.assert_called_once()
    routed_places = mock_build_route.call_args.args[0]
    assert [place.id for place in routed_places] == ["2", "3"]


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

    with patch.object(processor, "_generate_itinerary", new=AsyncMock(return_value=_make_itinerary())):
        result = await processor.process_message("Покажи достопримечательности Москвы", deps)

    assert isinstance(result, ProcessorResult)
    assert result.has_results is True
    assert result.route_geojson is None
    assert result.route_metadata is None
    # Поисковые результаты есть
    assert isinstance(result.response, list)


@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route")
async def test_verified_route_skips_itinerary_poi_from_another_city(mock_build_route, sample_places):
    """Координаты POI из другого города не попадают в маршрут выбранного города."""
    sample_places[2].city = "Сочи"
    processor = _make_processor()

    geojson, metadata = await processor._build_verified_route(
        _make_deps(),
        [{"query": "достопримечательности", "places": sample_places}],
        _make_itinerary(),
    )

    assert geojson is None
    assert metadata is None
    mock_build_route.assert_not_called()


@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route")
async def test_verified_route_skips_itinerary_poi_without_city_provenance(mock_build_route, sample_places):
    """Без города POI нельзя подтвердить как принадлежащий выбранному городу."""
    sample_places[2].city = None
    processor = _make_processor()

    geojson, metadata = await processor._build_verified_route(
        _make_deps(),
        [{"query": "достопримечательности", "places": sample_places}],
        _make_itinerary(),
    )

    assert geojson is None
    assert metadata is None
    mock_build_route.assert_not_called()


@pytest.mark.asyncio
@patch("app.core.services.processor.RouteService.build_route")
async def test_verified_route_skips_itinerary_with_unlocated_selected_poi(mock_build_route, sample_places):
    """Нельзя показывать частичную линию, если выбранная точка не имеет координат."""
    sample_places[2].latitude = None
    processor = _make_processor()

    geojson, metadata = await processor._build_verified_route(
        _make_deps(),
        [{"query": "достопримечательности", "places": sample_places}],
        _make_itinerary(),
    )

    assert geojson is None
    assert metadata is None
    mock_build_route.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(float("nan"), 37.6), (55.7, float("inf")), (91.0, 37.6), (55.7, -181.0)],
)
@patch("app.core.services.processor.RouteService.build_route")
async def test_verified_route_skips_selected_poi_with_invalid_coordinates(
    mock_build_route, sample_places, latitude, longitude
):
    """Координаты вне WGS84 или non-finite не передаются в router."""
    sample_places[2].latitude = latitude
    sample_places[2].longitude = longitude
    processor = _make_processor()

    geojson, metadata = await processor._build_verified_route(
        _make_deps(),
        [{"query": "достопримечательности", "places": sample_places}],
        _make_itinerary(),
    )

    assert geojson is None
    assert metadata is None
    mock_build_route.assert_not_called()


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
        "search_results", "itinerary", "suggested_replies", "follow_up_questions",
    }
    assert expected == field_names
