"""Сервис построения маршрутов через placesweb_backend."""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import httpx

from app.api.schemas import Place
from app.config.agent_settings import ROUTE_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Результат построения маршрута."""
    geojson: dict
    graph_id: str
    build_time_seconds: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    nodes_count: int = 0
    edges_count: int = 0
    alternatives_count: int = 0


class RouteService:
    """Сервис маршрутизации — вызывает placesweb_backend для построения графа маршрута."""

    @staticmethod
    async def build_route(
        places: List[Place],
        http_client: httpx.AsyncClient,
    ) -> Optional[RouteResult]:
        """
        Построить маршрут по списку мест.

        Graceful degradation: при любой ошибке логируем и возвращаем None,
        чтобы не ломать основной pipeline поиска мест.
        """
        try:
            points = RouteService._prepare_points(places)

            if len(points) < ROUTE_CONFIG["min_points"]:
                logger.info(
                    "Недостаточно точек для маршрута: %d (мин. %d)",
                    len(points),
                    ROUTE_CONFIG["min_points"],
                )
                return None

            response_data = await RouteService._call_graph_builder(
                points, http_client
            )
            return RouteService._parse_response(response_data)

        except Exception as e:
            logger.error("Ошибка построения маршрута: %s", e, exc_info=True)
            return None

    @staticmethod
    def _prepare_points(places: List[Place]) -> List[dict]:
        """Конвертировать Place → PointInput, отфильтровав места без координат."""
        points = []
        for place in places:
            if place.latitude is None or place.longitude is None:
                logger.debug("Пропуск места без координат: %s", place.name)
                continue

            # Clamp рейтинга к допустимому диапазону 0.1–10.0
            weight = ROUTE_CONFIG["default_weight"]
            if place.rating is not None:
                weight = max(0.1, min(10.0, place.rating))

            points.append({
                "lat": place.latitude,
                "lon": place.longitude,
                "weight": weight,
                "name": place.name or "Без названия",
            })
        return points

    @staticmethod
    async def _call_graph_builder(
        points: List[dict],
        http_client: httpx.AsyncClient,
    ) -> dict:
        """Отправить POST-запрос к placesweb_backend /api/v1/graph/build."""
        url = ROUTE_CONFIG["url"] + ROUTE_CONFIG["build_endpoint"]

        payload = {
            "points": points,
            "use_osrm_scoring": ROUTE_CONFIG["use_osrm_scoring"],
            "base_radius_m": ROUTE_CONFIG["base_radius_m"],
            "k_alternatives": ROUTE_CONFIG["k_alternatives"],
        }

        logger.info(
            "Запрос маршрута: %d точек → %s", len(points), url
        )

        response = await http_client.post(
            url,
            json=payload,
            timeout=ROUTE_CONFIG["timeout"],
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _parse_response(data: dict) -> RouteResult:
        """Распарсить ответ placesweb_backend в RouteResult."""
        alternatives = data.get("alternatives") or []
        return RouteResult(
            geojson=data.get("geojson", {}),
            graph_id=data.get("graph_id", ""),
            build_time_seconds=data.get("build_time_seconds", 0.0),
            metrics=data.get("metrics", {}),
            nodes_count=len(data.get("nodes", [])),
            edges_count=len(data.get("edges", [])),
            alternatives_count=len(alternatives),
        )
