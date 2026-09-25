"""Dependency-free tests for UTC league weeks and deterministic rank settlement."""

import unittest
from datetime import datetime, timezone

from app.core.league_policy import LeagueScore, league_week, settle_weekly_ranks


class LeagueWeekTests(unittest.TestCase):
    def test_week_uses_monday_utc_across_iso_year_boundary(self):
        week = league_week(datetime(2026, 1, 1, 12, tzinfo=timezone.utc))
        self.assertEqual("2026-W01", week.season_id)
        self.assertEqual(datetime(2025, 12, 29, tzinfo=timezone.utc), week.starts_at)
        self.assertEqual(datetime(2026, 1, 5, tzinfo=timezone.utc), week.ends_at)

    def test_week_normalizes_offset_before_selecting_iso_week(self):
        week = league_week(datetime.fromisoformat("2026-01-05T00:30:00+02:00"))
        self.assertEqual("2026-W01", week.season_id)
        self.assertEqual(datetime(2025, 12, 29, tzinfo=timezone.utc), week.starts_at)

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            league_week(datetime(2026, 9, 25))


class LeagueSettlementTests(unittest.TestCase):
    def test_top_and_bottom_fifth_move_one_rank(self):
        scores = [
            LeagueScore("a", 100, 4), LeagueScore("b", 80, 4),
            LeagueScore("c", 60, 4), LeagueScore("d", 40, 4),
            LeagueScore("e", 20, 4),
        ]
        settled = {row.user_id: row for row in settle_weekly_ranks(scores)}
        self.assertEqual((5, "promoted"), (settled["a"].rank_after, settled["a"].movement))
        self.assertEqual((3, "relegated"), (settled["e"].rank_after, settled["e"].movement))
        self.assertEqual("held", settled["c"].movement)

    def test_small_cohort_holds_and_equal_scores_share_place(self):
        scores = [LeagueScore("b", 10, 4), LeagueScore("a", 10, 4), LeagueScore("c", 0, 4)]
        settled = {row.user_id: row for row in settle_weekly_ranks(scores)}
        self.assertEqual(settled["a"].place, settled["b"].place)
        self.assertTrue(all(row.movement == "held" for row in settled.values()))

    def test_tie_at_both_cutoffs_does_not_split_cohort(self):
        scores = [
            LeagueScore("a", 100, 4), LeagueScore("b", 100, 4),
            LeagueScore("c", 100, 4), LeagueScore("d", 100, 4),
            LeagueScore("e", 100, 4),
        ]
        settled = settle_weekly_ranks(scores)
        self.assertTrue(all(row.movement == "held" for row in settled))

    def test_tie_at_promotion_cutoff_holds_but_clear_bottom_moves_down(self):
        scores = [
            LeagueScore("a", 100, 4), LeagueScore("b", 100, 4),
            LeagueScore("c", 80, 4), LeagueScore("d", 40, 4),
            LeagueScore("e", 20, 4),
        ]
        settled = {row.user_id: row for row in settle_weekly_ranks(scores)}
        self.assertEqual("held", settled["a"].movement)
        self.assertEqual("held", settled["b"].movement)
        self.assertEqual("relegated", settled["e"].movement)

    def test_tie_at_relegation_cutoff_holds_but_clear_top_moves_up(self):
        scores = [
            LeagueScore("a", 100, 4), LeagueScore("b", 80, 4),
            LeagueScore("c", 60, 4), LeagueScore("d", 20, 4),
            LeagueScore("e", 20, 4),
        ]
        settled = {row.user_id: row for row in settle_weekly_ranks(scores)}
        self.assertEqual("promoted", settled["a"].movement)
        self.assertEqual("held", settled["d"].movement)
        self.assertEqual("held", settled["e"].movement)

    def test_rank_changes_are_settled_within_each_rank_cohort(self):
        scores = [
            LeagueScore("a", 100, 2), LeagueScore("b", 80, 2),
            LeagueScore("c", 60, 2), LeagueScore("d", 40, 2),
            LeagueScore("e", 20, 2), LeagueScore("f", 1000, 3),
        ]
        settled = {row.user_id: row for row in settle_weekly_ranks(scores)}
        self.assertEqual("promoted", settled["a"].movement)
        self.assertEqual("relegated", settled["e"].movement)
        self.assertEqual("held", settled["f"].movement)

    def test_rank_changes_respect_floor_and_ceiling(self):
        scores = [
            LeagueScore("a", 100, 10), LeagueScore("b", 80, 5),
            LeagueScore("c", 60, 5), LeagueScore("d", 40, 5),
            LeagueScore("e", 20, 1),
        ]
        settled = {row.user_id: row for row in settle_weekly_ranks(scores)}
        self.assertEqual(10, settled["a"].rank_after)
        self.assertEqual(1, settled["e"].rank_after)
        self.assertEqual("held", settled["a"].movement)
        self.assertEqual("held", settled["e"].movement)

    def test_invalid_score_rows_are_rejected(self):
        with self.assertRaises(ValueError):
            settle_weekly_ranks([LeagueScore("a", -1, 1)])
        with self.assertRaises(ValueError):
            settle_weekly_ranks([LeagueScore("a", 0, 0)])
        with self.assertRaises(ValueError):
            settle_weekly_ranks([LeagueScore("a", 0, 1), LeagueScore("a", 2, 1)])


if __name__ == "__main__":
    unittest.main()
