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
