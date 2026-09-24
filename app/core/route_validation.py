"""Validation for route geometry returned by the routing service."""

from collections.abc import Mapping, Sequence
from math import isfinite


def has_renderable_route_line(geojson: object) -> bool:
    """Accept only FeatureCollections containing a usable WGS84 LineString."""
    if not isinstance(geojson, Mapping) or geojson.get("type") != "FeatureCollection":
        return False
    features = geojson.get("features")
    if not isinstance(features, list):
        return False

    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, Mapping) or geometry.get("type") != "LineString":
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue

        valid_line = True
        for position in coordinates:
            if (
                not isinstance(position, Sequence)
                or isinstance(position, (str, bytes))
                or len(position) < 2
            ):
                valid_line = False
                break
            longitude, latitude = position[0], position[1]
            if (
                not isinstance(longitude, (int, float))
                or not isinstance(latitude, (int, float))
                or not isfinite(longitude)
                or not isfinite(latitude)
                or not -180 <= longitude <= 180
                or not -90 <= latitude <= 90
            ):
                valid_line = False
                break
        if valid_line:
            return True
    return False
