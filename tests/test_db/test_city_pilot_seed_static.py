"""Dependency-free structural checks for the St Petersburg and Sochi pilots."""

import ast
import unittest
from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def assigned_literal(filename, name):
    tree = ast.parse((MIGRATIONS / filename).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} assignment not found in {filename}")


class CityPilotSeedStaticTests(unittest.TestCase):
    def test_both_five_node_paths_have_ordered_official_sources(self):
        initial = {
            "st-petersburg": assigned_literal(
                "m2a3b4c5d6e7_seed_st_petersburg_pilot_path.py", "entries"
            ),
            "sochi": assigned_literal(
                "n3b4c5d6e7f8_seed_sochi_pilot_path.py", "entries"
            ),
        }
        expansions = assigned_literal(
            "o4c5d6e7f8a9_expand_city_pilot_paths.py", "entries"
        )

        for city_id, base_entries in initial.items():
            rows = [(row[1], row[3], row[4], row[8]) for row in base_entries]
            rows.extend(
                (row[1], row[4], row[5], row[9])
                for row in expansions
                if row[2] == city_id
            )
            rows.sort(key=lambda row: row[1])

            self.assertEqual(len(rows), 5, city_id)
            self.assertEqual([row[1] for row in rows], [1, 2, 3, 4, 5], city_id)
            self.assertEqual(rows[0][2], None, city_id)
            self.assertEqual(
                [row[2] for row in rows[1:]],
                [row[0] for row in rows[:-1]],
                city_id,
            )
            for quest_id, _, _, source_url in rows:
                self.assertTrue(source_url.startswith("https://"), quest_id)
                self.assertTrue(
                    any(domain in source_url for domain in (
                        "hermitagemuseum.org", "peterhofmuseum.ru", "npsochi.ru",
                    )),
                    quest_id,
                )

    def test_each_pilot_exercises_fact_truth_myth_and_timeline(self):
        truth_myth = assigned_literal(
            "p5d6e7f8a9b0_add_city_truth_myth_lessons.py", "entries"
        )
        timelines = assigned_literal(
            "q6e7f8a9b0c1_add_city_timeline_lessons.py", "entries"
        )
        expected_truth = {"spb-peterhof-history", "sochi-park-area"}
        expected_timeline = {"spb-peterhof", "sochi-dendrarium"}
        self.assertEqual({row[1] for row in truth_myth}, expected_truth)
        self.assertEqual({row[1] for row in timelines}, expected_timeline)


if __name__ == "__main__":
    unittest.main()
