"""Dependency-free structural checks for the St Petersburg and Sochi pilots."""

import ast
import unittest
from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def assigned_literal(filename, name):
    tree = ast.parse((MIGRATIONS / filename).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} assignment not found in {filename}")


def content_payload(filename, content_id):
    tree = ast.parse((MIGRATIONS / filename).read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [key.value for key in node.keys if isinstance(key, ast.Constant)]
        if "id" not in keys or "payload" not in keys:
            continue
        values = dict(zip(keys, node.values))
        if isinstance(values["id"], ast.Constant) and values["id"].value == content_id:
            return ast.literal_eval(values["payload"])
    raise AssertionError(f"payload for {content_id} not found in {filename}")


def dict_literal_with_key(filename, id_value, required_keys):
    tree = ast.parse((MIGRATIONS / filename).read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [key.value if isinstance(key, ast.Constant) else None for key in node.keys]
        if not set(required_keys).issubset(keys) or "id" not in keys:
            continue
        values = dict(zip(keys, node.values))
        if isinstance(values["id"], ast.Constant) and values["id"].value == id_value:
            return {key: ast.literal_eval(values[key]) for key in required_keys}
    raise AssertionError(f"row {id_value} not found in {filename}")


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

    def test_moscow_english_editions_cover_the_route_and_preserve_canonical_answers(self):
        translations = assigned_literal(
            "y4c5d6e7f8a_add_moscow_english_quest_editions.py", "entries"
        )
        expected_revisions = {
            "moscow-red-square": "onboarding-moscow-v1",
            "moscow-spasskaya-tower": "moscow-spasskaya-v1",
            "moscow-tsar-bell": "moscow-tsar-bell-v1",
            "moscow-annunciation-cathedral": "moscow-annunciation-cathedral-v1",
            "moscow-gum": "moscow-gum-v1",
            "moscow-zaryadye": "moscow-zaryadye-v1",
            "moscow-tretyakov-gallery": "moscow-tretyakov-gallery-v1",
            "moscow-bolshoi-theatre": "moscow-bolshoi-theatre-v1",
            "moscow-metro": "moscow-metro-v1",
            "moscow-vdnh": "moscow-vdnh-v1",
        }
        self.assertEqual({entry["quest_id"] for entry in translations}, set(expected_revisions))

        canonical = {}
        canonical["moscow-red-square"] = content_payload(
            "a9c7d4e1f2b3_add_game_onboarding.py", "onboarding-moscow-v1"
        )
        canonical["moscow-spasskaya-tower"] = content_payload(
            "c5d6e7f8a9b0_add_spasskaya_quest_prerequisite.py", "moscow-spasskaya-v1"
        )
        canonical["moscow-tsar-bell"] = content_payload(
            "d6e7f8a9b0c1_add_moscow_goal_ledger_and_third_quest.py", "moscow-tsar-bell-v1"
        )
        moscow = assigned_literal("e7f8a9b0c1d2_add_moscow_tier_one_city_loop.py", "entries")
        for entry in moscow:
            canonical[entry["quest_id"]] = {
                "fact": {"source_url": entry["source_url"]},
                "question": {
                    "correct_option_id": entry["correct"],
                    "options": [{"id": key, "label": label} for key, label in entry["options"]],
                },
            }

        for entry in translations:
            quest_id = entry["quest_id"]
            self.assertEqual(entry["content_revision_id"], expected_revisions[quest_id])
            self.assertTrue(entry["title"].strip(), quest_id)
            self.assertTrue(entry["fact"].strip(), quest_id)
            self.assertTrue(entry["question"].strip(), quest_id)
            self.assertTrue(entry["stamp_title"].strip(), quest_id)
            self.assertTrue(entry["source_label"].strip(), quest_id)
            self.assertNotIn("source_url", entry)
            translated_options = {key for key, label in entry["options"] if key and label}
            question = canonical[quest_id]["question"]
            canonical_options = {option["id"] for option in question["options"]}
            self.assertEqual(translated_options, canonical_options, quest_id)
            self.assertIn(question["correct_option_id"], translated_options, quest_id)
            self.assertTrue(canonical[quest_id]["fact"]["source_url"].startswith("https://"), quest_id)

    def test_moscow_boss_english_edition_keeps_questions_answers_and_sources(self):
        translated = assigned_literal(
            "z5d6e7f8a9b_add_moscow_boss_english_edition.py", "payload"
        )
        canonical = content_payload(
            "f9a0b1c2d3e4_add_moscow_city_boss.py", "moscow-city-boss-v1"
        )
        expected_questions = {question["id"]: question for question in canonical["questions"]}
        self.assertEqual({question["id"] for question in translated["questions"]}, set(expected_questions))
        for question in translated["questions"]:
            source = expected_questions[question["id"]]
            self.assertTrue(question["text"].strip(), question["id"])
            self.assertNotIn("correct_option_id", question)
            self.assertEqual(
                {option[0] for option in question["options"]},
                {option["id"] for option in source["options"]},
                question["id"],
            )
            self.assertTrue(question["explanation"].strip(), question["id"])
        self.assertEqual(
            [source["url"] for source in translated["sources"]],
            [source["url"] for source in canonical["sources"]],
        )

    def test_moscow_sandbox_story_translation_only_overlays_display_text(self):
        translated = assigned_literal(
            "z6e7f8a9b0c_localize_moscow_sandbox_story.py", "payload"
        )["story"]
        self.assertEqual(
            assigned_literal("z6e7f8a9b0c_localize_moscow_sandbox_story.py", "CONTENT_REVISION_ID"),
            "moscow-sandbox-activities-v8",
        )
        self.assertNotIn("source_url", translated)
        self.assertNotIn("image_url", translated)
        for key in ("title", "eyebrow", "image_alt", "media_credit", "fact", "source_label", "note"):
            self.assertTrue(translated[key].strip(), key)

    def test_moscow_sandbox_activity_edition_keeps_ids_and_scoring_canonical(self):
        translated = assigned_literal(
            "z7f8a9b0c1d_localize_moscow_sandbox_activities.py", "activity_payload"
        )
        self.assertEqual(set(translated), {
            "truth_myth", "matching", "timeline", "word_blocks", "price_slider", "photo_scanner",
        })
        self.assertEqual(
            {item["id"] for item in translated["truth_myth"]["statements"]},
            {"zaryadye-2017", "metro-1954", "gum-1893"},
        )
        self.assertEqual(
            {item["id"] for item in translated["matching"]["pairs"]},
            {"cathedral-year", "gum-year", "vdnh-year"},
        )
        self.assertEqual(
            {item["id"] for item in translated["matching"]["choices"]},
            {"year-1489", "year-1893", "year-1939"},
        )
        self.assertEqual(
            {item["id"] for item in translated["timeline"]["items"]},
            {"metro-1935", "gum-1893", "vdnh-1939"},
        )
        self.assertEqual(
            {item["id"] for item in translated["word_blocks"]["blocks"]},
            {"word-capital", "word-russia", "word-moscow", "word-dash"},
        )
        for section, collection, key in (
            ("truth_myth", "statements", "text"), ("matching", "pairs", "left"),
            ("matching", "choices", "label"), ("timeline", "items", "label"),
            ("word_blocks", "blocks", "label"),
        ):
            self.assertTrue(all(item[key].strip() for item in translated[section][collection]))
        for section in ("truth_myth", "matching", "timeline", "word_blocks", "price_slider", "photo_scanner"):
            self.assertTrue(translated[section].get("title", "").strip(), section)
            self.assertNotIn("correct_answer", translated[section], section)
            self.assertNotIn("correct_choice_id", translated[section], section)
            self.assertNotIn("expected_order", translated[section], section)
            self.assertNotIn("target", translated[section], section)
            self.assertNotIn("tolerance", translated[section], section)
            self.assertNotIn("hotspots", translated[section], section)
            self.assertNotIn("source_url", translated[section], section)

    def test_english_moscow_wiki_is_a_separate_published_edition_with_same_sources(self):
        migration = "z8f9a0b1c2d3_seed_moscow_wiki_english.py"
        body = assigned_literal(migration, "ENGLISH_BODY")
        sources = assigned_literal(migration, "SOURCES")
        canonical = dict_literal_with_key(
            "i8d9e0f1a2b3_seed_moscow_wiki_article.py", "wiki-moscow-v1", ("body", "sources", "license")
        )
        self.assertEqual(
            assigned_literal(migration, "revision"), "z8f9a0b1c2d3",
        )
        self.assertEqual(
            assigned_literal(migration, "down_revision"), "z7f8a9b0c1d",
        )
        self.assertEqual(assigned_literal(migration, "ARTICLE_ID"), "wiki-moscow-en")
        self.assertEqual(assigned_literal(migration, "ARTICLE_SLUG"), "moscow-en")
        self.assertEqual(assigned_literal(migration, "VERSION_ID"), "wiki-moscow-en-v1")
        self.assertTrue(body["summary"].strip())
        self.assertEqual(len(body["sections"]), len(canonical["body"]["sections"]))
        self.assertTrue(all(section["title"].strip() and section["text"].strip() for section in body["sections"]))
        self.assertEqual([source["url"] for source in sources], [source["url"] for source in canonical["sources"]])
        self.assertTrue(all(source["label"].strip() for source in sources))
        self.assertEqual(assigned_literal(migration, "LICENSE"), canonical["license"])

    def test_english_country_wiki_editions_preserve_source_urls(self):
        migration = "z9a0b1c2d3e4_publish_english_country_wiki.py"
        editions = assigned_literal(migration, "EDITIONS")
        self.assertEqual({edition["country"] for edition in editions}, {"ru", "jp", "ge"})
        canonical_migrations = {
            "ru": ("v1d2e3f4a5b_publish_russia_wiki_article.py", "wiki-country-ru-v1"),
            "jp": ("t9b0c1d2e3f4_publish_japan_wiki_article.py", "wiki-country-jp-v1"),
            "ge": ("u0c1d2e3f4a_publish_georgia_wiki_article.py", "wiki-country-ge-v1"),
        }
        for edition in editions:
            filename, version_id = canonical_migrations[edition["country"]]
            canonical = dict_literal_with_key(filename, version_id, ("body", "sources", "license"))
            self.assertTrue(edition["title"].strip(), edition["country"])
            self.assertEqual(
                [source["url"] for source in edition["sources"]],
                [source["url"] for source in canonical["sources"]],
                edition["country"],
            )
            for field in ("summary", "history", "cuisine", "traditions"):
                self.assertTrue(edition["body"][field].strip(), (edition["country"], field))
            self.assertTrue(all(
                row["label"].strip() and row["value"].strip()
                for row in edition["body"]["practical"]
            ), edition["country"])
        self.assertEqual(assigned_literal(migration, "LICENSE"), "CC BY 4.0")
        self.assertEqual(assigned_literal(migration, "down_revision"), "z8f9a0b1c2d3")


if __name__ == "__main__":
    unittest.main()
