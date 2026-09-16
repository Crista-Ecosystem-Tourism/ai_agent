import unittest

from app.db.migrate import _can_adopt_legacy_revisions


class MigrationAdoptionTests(unittest.TestCase):
    def test_adopts_only_known_nonempty_legacy_revisions(self):
        self.assertTrue(_can_adopt_legacy_revisions({"head"}, {"base", "head"}))

    def test_refuses_unknown_or_empty_legacy_revisions(self):
        self.assertFalse(_can_adopt_legacy_revisions({"other-service-head"}, {"head"}))
        self.assertFalse(_can_adopt_legacy_revisions(set(), {"head"}))
