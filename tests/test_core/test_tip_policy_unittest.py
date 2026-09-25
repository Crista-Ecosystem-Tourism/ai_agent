import unittest

from app.core.tip_policy import clean_moderation_note, clean_tip_body


class TipPolicyTests(unittest.TestCase):
    def test_tip_body_collapses_whitespace(self):
        self.assertEqual(clean_tip_body("  Good   shoes\nhelp here. "), "Good shoes help here.")

    def test_tip_body_rejects_too_short_or_too_long_text(self):
        for body in ("short", "x" * 1201):
            with self.subTest(body_length=len(body)), self.assertRaises(ValueError):
                clean_tip_body(body)

    def test_moderation_note_is_optional_and_normalized(self):
        self.assertIsNone(clean_moderation_note("  \n "))
        self.assertEqual(clean_moderation_note("  Needs   a source "), "Needs a source")

    def test_moderation_note_has_a_hard_length_limit(self):
        with self.assertRaises(ValueError):
            clean_moderation_note("x" * 501)


if __name__ == "__main__":
    unittest.main()
