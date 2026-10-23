"""Dependency-free tests for calendar-day streaks."""

import unittest
from datetime import date

from app.core.streak_policy import next_streak, visible_streak


class NextStreakTests(unittest.TestCase):
    def test_first_activity_starts_at_one(self):
        self.assertEqual(1, next_streak(0, None, date(2026, 10, 1)))

    def test_second_activity_on_same_day_does_not_extend(self):
        self.assertEqual(3, next_streak(3, date(2026, 10, 1), date(2026, 10, 1)))

    def test_consecutive_day_extends(self):
        self.assertEqual(4, next_streak(3, date(2026, 10, 1), date(2026, 10, 2)))

    def test_missed_day_restarts(self):
        self.assertEqual(1, next_streak(9, date(2026, 10, 1), date(2026, 10, 3)))

    def test_month_boundary_counts_as_consecutive(self):
        self.assertEqual(2, next_streak(1, date(2026, 9, 30), date(2026, 10, 1)))


class VisibleStreakTests(unittest.TestCase):
    def test_no_activity_is_zero(self):
        self.assertEqual(0, visible_streak(0, None, date(2026, 10, 5)))

    def test_activity_today_is_kept(self):
        self.assertEqual(5, visible_streak(5, date(2026, 10, 5), date(2026, 10, 5)))

    def test_activity_yesterday_is_kept_until_today_ends(self):
        self.assertEqual(5, visible_streak(5, date(2026, 10, 4), date(2026, 10, 5)))

    def test_missed_day_shows_broken_streak_without_write(self):
        self.assertEqual(0, visible_streak(5, date(2026, 10, 3), date(2026, 10, 5)))


if __name__ == "__main__":
    unittest.main()
