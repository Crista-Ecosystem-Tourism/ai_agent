"""Tests for SavedRouteService CRUD and ownership checks."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.saved_route import SavedRouteService


def _make_mock_session_factory():
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock()
    factory.return_value = mock_db
    return factory, mock_db


@pytest.fixture
def route_service():
    factory, mock_db = _make_mock_session_factory()
    service = SavedRouteService(factory)
    service._mock_db = mock_db
    return service


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_id(self, route_service):
        route_id = await route_service.create("user-1", {
            "name": "Мой маршрут",
            "destination": "Москва",
            "places": [{"id": "p1", "name": "Place 1"}],
        })
        assert isinstance(route_id, str)
        assert len(route_id) == 32  # UUID hex
        route_service._mock_db.execute.assert_called_once()
        route_service._mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_optional_fields(self, route_service):
        route_id = await route_service.create("user-1", {
            "name": "С паутинкой",
            "destination": "Сочи",
            "session_id": "session-123",
            "places": [{"id": "p1"}],
            "graph_geojson": {"type": "FeatureCollection", "features": []},
        })
        assert isinstance(route_id, str)


class TestListForUser:
    @pytest.mark.asyncio
    async def test_list_returns_routes(self, route_service):
        mock_row = MagicMock()
        mock_row.id = "r1"
        mock_row.name = "Route 1"
        mock_row.destination = "Москва"
        mock_row.created_at = MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:00"))
        mock_row.updated_at = MagicMock(isoformat=MagicMock(return_value="2026-01-02T00:00:00"))

        route_service._mock_db.execute.return_value = MagicMock(
            all=MagicMock(return_value=[mock_row])
        )
        result = await route_service.list_for_user("user-1")
        assert len(result) == 1
        assert result[0]["id"] == "r1"
        assert result[0]["name"] == "Route 1"

    @pytest.mark.asyncio
    async def test_list_empty(self, route_service):
        route_service._mock_db.execute.return_value = MagicMock(
            all=MagicMock(return_value=[])
        )
        result = await route_service.list_for_user("user-1")
        assert result == []


class TestGetOwned:
    @pytest.mark.asyncio
    async def test_get_owned_success(self, route_service):
        mock_row = MagicMock()
        mock_row.id = "r1"
        mock_row.user_id = "user-1"
        mock_row.name = "Route 1"
        mock_row.destination = "Москва"
        mock_row.session_id = None
        mock_row.places = [{"id": "p1"}]
        mock_row.graph_geojson = None
        mock_row.created_at = MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:00"))
        mock_row.updated_at = MagicMock(isoformat=MagicMock(return_value="2026-01-02T00:00:00"))

        route_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_row)
        )
        result = await route_service.get_owned("r1", "user-1")
        assert result is not None
        assert result["id"] == "r1"
        assert result["places"] == [{"id": "p1"}]

    @pytest.mark.asyncio
    async def test_get_owned_wrong_user(self, route_service):
        mock_row = MagicMock()
        mock_row.user_id = "user-1"

        route_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_row)
        )
        result = await route_service.get_owned("r1", "user-other")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_owned_not_found(self, route_service):
        route_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        result = await route_service.get_owned("r-nonexistent", "user-1")
        assert result is None


class TestDeleteOwned:
    @pytest.mark.asyncio
    async def test_delete_owned_success(self, route_service):
        route_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value="user-1")
        )
        result = await route_service.delete_owned("r1", "user-1")
        assert result is True
        route_service._mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_owned_wrong_user(self, route_service):
        route_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value="user-1")
        )
        result = await route_service.delete_owned("r1", "user-other")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_owned_not_found(self, route_service):
        route_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        result = await route_service.delete_owned("r-nonexistent", "user-1")
        assert result is False
