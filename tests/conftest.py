"""Фикстуры для тестов ai_agent."""

import pytest
from app.api.schemas import Place


# ---------------------------------------------------------------------------
# Мок-данные: места
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_places() -> list[Place]:
    """Список мест с координатами и рейтингом."""
    return [
        Place(
            id="1",
            name="Красная площадь",
            city="Москва",
            country="Россия",
            description="Главная площадь Москвы",
            latitude=55.7539,
            longitude=37.6208,
            rating=4.8,
            review_count=12000,
            subtype="достопримечательность",
        ),
        Place(
            id="2",
            name="Третьяковская галерея",
            city="Москва",
            country="Россия",
            description="Знаменитый музей русского искусства",
            latitude=55.7415,
            longitude=37.6208,
            rating=4.7,
            review_count=8500,
            subtype="музей",
        ),
        Place(
            id="3",
            name="Парк Горького",
            city="Москва",
            country="Россия",
            description="Центральный парк культуры и отдыха",
            latitude=55.7312,
            longitude=37.6031,
            rating=4.6,
            review_count=9500,
            subtype="парк",
        ),
    ]


@pytest.fixture
def places_without_coords() -> list[Place]:
    """Места без координат — должны фильтроваться RouteService."""
    return [
        Place(id="10", name="Без координат 1", latitude=None, longitude=None),
        Place(id="11", name="Без координат 2", latitude=None, longitude=None),
    ]


@pytest.fixture
def mixed_places(sample_places, places_without_coords) -> list[Place]:
    """Смешанный список: часть с координатами, часть без."""
    return sample_places + places_without_coords


@pytest.fixture
def places_extreme_rating() -> list[Place]:
    """Места с рейтингом за пределами допустимого диапазона 0.1–10.0."""
    return [
        Place(id="20", name="Рейтинг ноль", latitude=55.0, longitude=37.0, rating=0.0),
        Place(id="21", name="Рейтинг отрицательный", latitude=55.1, longitude=37.1, rating=-5.0),
        Place(id="22", name="Рейтинг огромный", latitude=55.2, longitude=37.2, rating=99.0),
    ]


# ---------------------------------------------------------------------------
# Мок-данные: ответ placesweb_backend
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_route_response() -> dict:
    """Успешный ответ от placesweb_backend /api/v1/graph/build."""
    return {
        "graph_id": "test-graph-123",
        "nodes": [
            {"id": 0, "lat": 55.7539, "lon": 37.6208, "weight": 4.8, "name": "Красная площадь"},
            {"id": 1, "lat": 55.7415, "lon": 37.6208, "weight": 4.7, "name": "Третьяковская галерея"},
            {"id": 2, "lat": 55.7312, "lon": 37.6031, "weight": 4.6, "name": "Парк Горького"},
        ],
        "edges": [
            {
                "from_node": {"id": 0, "lat": 55.7539, "lon": 37.6208, "weight": 4.8, "name": "Красная площадь"},
                "to_node": {"id": 1, "lat": 55.7415, "lon": 37.6208, "weight": 4.7, "name": "Третьяковская галерея"},
                "distance_m": 1380.0,
                "route_geometry": [[37.6208, 55.7539], [37.6208, 55.7415]],
            },
            {
                "from_node": {"id": 1, "lat": 55.7415, "lon": 37.6208, "weight": 4.7, "name": "Третьяковская галерея"},
                "to_node": {"id": 2, "lat": 55.7312, "lon": 37.6031, "weight": 4.6, "name": "Парк Горького"},
                "distance_m": 1540.0,
                "route_geometry": [[37.6208, 55.7415], [37.6031, 55.7312]],
            },
        ],
        "metrics": {
            "num_vertices": 3,
            "num_edges": 2,
            "avg_degree": 1.33,
            "graph_density": 0.67,
            "avg_edge_distance_m": 1460.0,
        },
        "alternatives": [
            {"path_nodes": [0, 1, 2], "distance_m": 2920.0, "route_geometry": []},
        ],
        "build_time_seconds": 1.23,
        "geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [37.6208, 55.7539]},
                    "properties": {"name": "Красная площадь", "weight": 4.8},
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# Мок-данные: результаты поиска (формат _execute_search_queries)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_search_results(sample_places) -> list[dict]:
    """Результаты поиска в формате, возвращаемом _execute_search_queries."""
    return [
        {
            "query": "достопримечательности Москва",
            "places": sample_places,
        }
    ]
