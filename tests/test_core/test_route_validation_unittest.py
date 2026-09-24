"""Dependency-free tests for routing-service GeoJSON validation."""

import unittest

from app.core.route_validation import has_renderable_route_line


def feature_collection(coordinates):
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coordinates},
            "properties": {},
        }],
    }


class RouteGeometryValidationTests(unittest.TestCase):
    def test_accepts_valid_line(self):
        self.assertTrue(has_renderable_route_line(feature_collection([[37.6, 55.7], [37.7, 55.8]])))

    def test_rejects_missing_or_wrong_geojson_structure(self):
        self.assertFalse(has_renderable_route_line(None))
        self.assertFalse(has_renderable_route_line({"type": "FeatureCollection", "features": []}))
        self.assertFalse(has_renderable_route_line({"type": "FeatureCollection", "features": "bad"}))

    def test_rejects_short_or_invalid_line(self):
        self.assertFalse(has_renderable_route_line(feature_collection([[37.6, 55.7]])))
        self.assertFalse(has_renderable_route_line(feature_collection([[37.6, 55.7], [181, 55.8]])))
        invalid = feature_collection([[37.6, 55.7], [37.7, float("nan")]])
        self.assertFalse(has_renderable_route_line(invalid))

    def test_point_features_alone_are_not_a_route(self):
        self.assertFalse(has_renderable_route_line({
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [37.6, 55.7]}}],
        }))


if __name__ == "__main__":
    unittest.main()
