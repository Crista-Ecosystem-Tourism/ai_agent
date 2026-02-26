"""Тесты для RouteService — построение маршрутов через placesweb_backend."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.services.route import RouteService, RouteResult
from app.api.schemas import Place


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# 1. Успешное построение маршрута
# ---------------------------------------------------------------------------

async def test_build_route_success(sample_places, mock_route_response):
    """При корректных данных RouteService возвращает RouteResult с GeoJSON."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_route_response
    mock_response.raise_for_status = MagicMock()

    http_client = AsyncMock(spec=httpx.AsyncClient)
    http_client.post.return_value = mock_response

    result = await RouteService.build_route(sample_places, http_client)

    assert result is not None
    assert isinstance(result, RouteResult)
    assert result.geojson["type"] == "FeatureCollection"
    assert result.graph_id == "test-graph-123"
    assert result.nodes_count == 3
    assert result.edges_count == 2
    assert result.alternatives_count == 1
    assert result.build_time_seconds == 1.23

    # Проверяем, что HTTP-запрос был отправлен
    http_client.post.assert_called_once()
    call_kwargs = http_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert len(payload["points"]) == 3


# ---------------------------------------------------------------------------
# 2. Фильтрация мест без координат
# ---------------------------------------------------------------------------

async def test_build_route_filters_places_without_coords(
    mixed_places, mock_route_response
):
    """Места без lat/lon отфильтровываются, маршрут строится по оставшимся."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_route_response
    mock_response.raise_for_status = MagicMock()

    http_client = AsyncMock(spec=httpx.AsyncClient)
    http_client.post.return_value = mock_response

    result = await RouteService.build_route(mixed_places, http_client)

    assert result is not None
    # В payload должно быть только 3 точки (с координатами), а не 5
    payload = http_client.post.call_args.kwargs.get("json") or http_client.post.call_args[1].get("json")
    assert len(payload["points"]) == 3


# ---------------------------------------------------------------------------
# 3. Меньше 2 мест → None
# ---------------------------------------------------------------------------

async def test_build_route_too_few_places():
    """Если после фильтрации осталось < 2 точек, возвращаем None."""
    single_place = [
        Place(id="1", name="Одинокое место", latitude=55.0, longitude=37.0)
    ]
    http_client = AsyncMock(spec=httpx.AsyncClient)

    result = await RouteService.build_route(single_place, http_client)

    assert result is None
    # HTTP-запрос не должен отправляться
    http_client.post.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Clamp рейтинга к диапазону 0.1–10.0
# ---------------------------------------------------------------------------

async def test_prepare_points_clamps_rating(places_extreme_rating):
    """Рейтинг 0.0 → 0.1, -5.0 → 0.1, 99.0 → 10.0."""
    points = RouteService._prepare_points(places_extreme_rating)

    assert len(points) == 3
    assert points[0]["weight"] == 0.1   # было 0.0
    assert points[1]["weight"] == 0.1   # было -5.0
    assert points[2]["weight"] == 10.0  # было 99.0


# ---------------------------------------------------------------------------
# 5. Таймаут placesweb → None (graceful degradation)
# ---------------------------------------------------------------------------

async def test_build_route_timeout_returns_none(sample_places):
    """При таймауте запроса к placesweb_backend возвращаем None."""
    http_client = AsyncMock(spec=httpx.AsyncClient)
    http_client.post.side_effect = httpx.ReadTimeout("Таймаут запроса")

    result = await RouteService.build_route(sample_places, http_client)

    assert result is None


# ---------------------------------------------------------------------------
# 6. HTTP 500 от placesweb → None (graceful degradation)
# ---------------------------------------------------------------------------

async def test_build_route_server_error_returns_none(sample_places):
    """При 500 от placesweb_backend возвращаем None."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Internal Server Error",
        request=MagicMock(),
        response=mock_response,
    )

    http_client = AsyncMock(spec=httpx.AsyncClient)
    http_client.post.return_value = mock_response

    result = await RouteService.build_route(sample_places, http_client)

    assert result is None


# ---------------------------------------------------------------------------
# 7. Пустой список → None
# ---------------------------------------------------------------------------

async def test_build_route_empty_list():
    """Пустой список мест → None без HTTP-запросов."""
    http_client = AsyncMock(spec=httpx.AsyncClient)

    result = await RouteService.build_route([], http_client)

    assert result is None
    http_client.post.assert_not_called()
