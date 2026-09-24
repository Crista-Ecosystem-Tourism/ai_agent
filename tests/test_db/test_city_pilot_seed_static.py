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
        for row in truth_myth:
            quest_id, fact_text, source_url = row[1], row[4], row[6]
            correct_option_id = row[8]
            self.assertEqual(correct_option_id, "fact", quest_id)
            self.assertIn("относится к 1705 году" if quest_id.startswith("spb-") else "214 098,6", fact_text)
            self.assertTrue(source_url.startswith("https://"), quest_id)

    def test_english_editions_cover_all_pilot_quests_and_keep_answer_ids(self):
        translations = assigned_literal(
            "x3b4c5d6e7f8_add_city_quest_translations.py", "entries"
        )
        expected_ids = {
            "spb-hermitage", "spb-peterhof", "spb-collection", "spb-fountains",
            "spb-peterhof-history", "sochi-national-park", "sochi-dendrarium",
            "sochi-forest", "sochi-mzymta", "sochi-park-area",
        }
        self.assertEqual({row[0] for row in translations}, expected_ids)
        for quest_id, title, fact, _source, question, options, stamp in translations:
            self.assertTrue(title.strip(), quest_id)
            self.assertTrue(fact.strip(), quest_id)
            self.assertTrue(question.strip(), quest_id)
            self.assertTrue(stamp.strip(), quest_id)
            self.assertTrue(all(key and label for key, label in options), quest_id)
        canonical_options = {}
        initial_spb = assigned_literal("m2a3b4c5d6e7_seed_st_petersburg_pilot_path.py", "entries")
        initial_sochi = assigned_literal("n3b4c5d6e7f8_seed_sochi_pilot_path.py", "entries")
        expanded = assigned_literal("o4c5d6e7f8a9_expand_city_pilot_paths.py", "entries")
        for row in [*initial_spb, *initial_sochi]:
            canonical_options[row[1]] = {"correct": row[10], "options": set(row[11])}
        for row in expanded:
            canonical_options[row[1]] = {"correct": row[11], "options": set(row[12])}
        truth_myth = assigned_literal("p5d6e7f8a9b0_add_city_truth_myth_lessons.py", "entries")
        for row in truth_myth:
            canonical_options[row[1]] = {"correct": row[8], "options": {"fact", "myth"}}
        timelines = assigned_literal("q6e7f8a9b0c1_add_city_timeline_lessons.py", "entries")
        for row in timelines:
            canonical_options[row[1]] = {"correct": row[8], "options": set(row[9])}
        for quest_id, _title, _fact, _source, _question, options, _stamp in translations:
            translated_ids = {key for key, _label in options}
            self.assertEqual(translated_ids, canonical_options[quest_id]["options"], quest_id)
            self.assertIn(canonical_options[quest_id]["correct"], translated_ids, quest_id)

        expected_timeline_answers = {
            "spb-peterhof": ("1723", "15 августа 1723 года"),
            "sochi-dendrarium": ("1892", "завершены в 1892 году"),
        }
        for row in timelines:
            quest_id, fact_text, source_url = row[1], row[4], row[6]
            correct_answer, supported_phrase = expected_timeline_answers[quest_id]
            self.assertEqual(row[8], correct_answer, quest_id)
            self.assertIn(correct_answer, row[9], quest_id)
            self.assertIn(supported_phrase, fact_text, quest_id)
            self.assertTrue(source_url.startswith("https://"), quest_id)


if __name__ == "__main__":
    unittest.main()
