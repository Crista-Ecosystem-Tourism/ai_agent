"""Tests for place_ratings and graph_geojson persistence on ChatSession."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat_session import ChatSessionService


def _make_mock_session_factory():
    """Create a mock async session factory for testing."""
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock()
    factory.return_value = mock_db
    return factory, mock_db


@pytest.fixture
def chat_service():
    factory, mock_db = _make_mock_session_factory()
    service = ChatSessionService(factory)
    service._mock_db = mock_db
    return service


class TestPlaceRatings:
    @pytest.mark.asyncio
    async def test_save_place_ratings(self, chat_service):
        ratings = {"place1": {"rating": 4, "score": 3, "selected": True}}
        await chat_service.save_place_ratings("session-1", ratings)
        chat_service._mock_db.execute.assert_called_once()
        chat_service._mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_place_ratings_returns_data(self, chat_service):
        expected = {"place1": {"rating": 5, "score": None, "selected": False}}
        chat_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=expected)
        )
        result = await chat_service.load_place_ratings("session-1")
        assert result == expected

    @pytest.mark.asyncio
    async def test_load_place_ratings_returns_none(self, chat_service):
        chat_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        result = await chat_service.load_place_ratings("session-1")
        assert result is None


class TestGraphGeoJSON:
    @pytest.mark.asyncio
    async def test_save_graph_geojson(self, chat_service):
        geojson = {"type": "FeatureCollection", "features": []}
        await chat_service.save_graph_geojson("session-1", geojson)
        chat_service._mock_db.execute.assert_called_once()
        chat_service._mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_graph_geojson_returns_data(self, chat_service):
        expected = {"type": "FeatureCollection", "features": [{"type": "Feature"}]}
        chat_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=expected)
        )
        result = await chat_service.load_graph_geojson("session-1")
        assert result == expected

    @pytest.mark.asyncio
    async def test_load_graph_geojson_returns_none(self, chat_service):
        chat_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        result = await chat_service.load_graph_geojson("session-1")
        assert result is None


class TestRoundTrip:
    @pytest.mark.asyncio
    async def test_save_and_load_ratings_roundtrip(self, chat_service):
        """Verify save followed by load returns the same data."""
        ratings = {
            "p1": {"rating": 4, "score": 3, "selected": True},
            "p2": {"rating": 2, "score": None, "selected": False},
        }
        await chat_service.save_place_ratings("sess-rt", ratings)
        # Simulate load returning what was saved
        chat_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=ratings)
        )
        loaded = await chat_service.load_place_ratings("sess-rt")
        assert loaded == ratings

    @pytest.mark.asyncio
    async def test_save_and_load_graph_roundtrip(self, chat_service):
        """Verify save followed by load returns the same data."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [37.6, 55.7]}}
            ],
        }
        await chat_service.save_graph_geojson("sess-rt", geojson)
        chat_service._mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=geojson)
        )
        loaded = await chat_service.load_graph_geojson("sess-rt")
        assert loaded == geojson
