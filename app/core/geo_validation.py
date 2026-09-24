"""Dependency-free validation helpers for geographic coordinates."""

import math


def has_valid_coordinates(latitude: float | None, longitude: float | None) -> bool:
    """Return whether coordinates are finite values within WGS84 ranges."""
    if latitude is None or longitude is None:
        return False
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def belongs_to_city(place_city: str | None, expected_city: str | None) -> bool:
    """Require a known matching city; unknown provenance is not route-safe."""
    if not place_city or not expected_city:
        return False
    return place_city.strip().casefold() == expected_city.strip().casefold()
