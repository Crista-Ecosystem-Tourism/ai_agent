"""Тесты для API-схем — MessageOut, Place."""

import pytest

from app.api.schemas import MessageOut, SearchResult, Place


# ---------------------------------------------------------------------------
# 1. MessageOut с маршрутом
# ---------------------------------------------------------------------------

def test_message_out_with_route():
    """MessageOut корректно сериализуется с route_geojson и route_metadata."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [37.62, 55.75]},
                "properties": {"name": "Красная площадь"},
            }
        ],
    }
    metadata = {
        "graph_id": "abc-123",
        "build_time_seconds": 0.5,
        "nodes_count": 3,
    }

    msg = MessageOut(
        message="Вот ваши места!",
        has_search_results=True,
        conversation_complete=False,
        route_geojson=geojson,
        route_metadata=metadata,
    )

    assert msg.route_geojson is not None
    assert msg.route_geojson["type"] == "FeatureCollection"
    assert msg.route_metadata["graph_id"] == "abc-123"

    # Проверяем JSON-сериализацию
    data = msg.model_dump()
    assert "route_geojson" in data
    assert "route_metadata" in data
    assert data["route_geojson"]["type"] == "FeatureCollection"


# ---------------------------------------------------------------------------
# 2. MessageOut без маршрута (обратная совместимость)
# ---------------------------------------------------------------------------

def test_message_out_without_route():
    """MessageOut по умолчанию возвращает route_geojson=None, route_metadata=None."""
    msg = MessageOut(
        message="Привет! Куда вы хотите поехать?",
        has_search_results=False,
        conversation_complete=False,
    )

    assert msg.route_geojson is None
    assert msg.route_metadata is None

    data = msg.model_dump()
    assert data["route_geojson"] is None
    assert data["route_metadata"] is None


# ---------------------------------------------------------------------------
# 3. Place → dict конвертация
# ---------------------------------------------------------------------------

def test_place_to_dict():
    """Place корректно сериализуется в dict с координатами и рейтингом."""
    place = Place(
        id="1",
        name="Тестовое место",
        city="Москва",
        country="Россия",
        description="Описание",
        latitude=55.75,
        longitude=37.62,
        rating=4.5,
        review_count=100,
        subtype="кафе",
    )

    data = place.model_dump()

    assert data["name"] == "Тестовое место"
    assert data["latitude"] == 55.75
    assert data["longitude"] == 37.62
    assert data["rating"] == 4.5
    assert data["city"] == "Москва"
