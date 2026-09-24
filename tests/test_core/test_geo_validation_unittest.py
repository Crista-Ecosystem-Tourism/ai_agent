"""Dependency-free regression coverage for WGS84 coordinate validation."""

import math
import unittest

from app.core.geo_validation import belongs_to_city, has_valid_coordinates


class CoordinateValidationTests(unittest.TestCase):
    def test_accepts_valid_wgs84_boundaries(self):
        self.assertTrue(has_valid_coordinates(-90, -180))
        self.assertTrue(has_valid_coordinates(90, 180))
        self.assertTrue(has_valid_coordinates(55.75, 37.62))

    def test_rejects_missing_coordinates(self):
        self.assertFalse(has_valid_coordinates(None, 37.62))
        self.assertFalse(has_valid_coordinates(55.75, None))

    def test_rejects_non_finite_coordinates(self):
        self.assertFalse(has_valid_coordinates(math.nan, 37.62))
        self.assertFalse(has_valid_coordinates(55.75, math.inf))
        self.assertFalse(has_valid_coordinates(-math.inf, 37.62))

    def test_rejects_coordinates_outside_wgs84_ranges(self):
        self.assertFalse(has_valid_coordinates(90.0001, 37.62))
        self.assertFalse(has_valid_coordinates(55.75, -180.0001))

    def test_city_match_is_case_and_whitespace_insensitive(self):
        self.assertTrue(belongs_to_city(" Москва ", "москва"))

    def test_city_match_rejects_unknown_or_different_city(self):
        self.assertFalse(belongs_to_city(None, "Москва"))
        self.assertFalse(belongs_to_city("", "Москва"))
        self.assertFalse(belongs_to_city("Сочи", "Москва"))
        self.assertFalse(belongs_to_city("Москва", None))


if __name__ == "__main__":
    unittest.main()
