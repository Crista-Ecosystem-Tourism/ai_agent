import unittest

from app.db.models.base import Base
from app.db.models import auth, chat, saved_route  # noqa: F401
from app.db.migrate import VERSION_TABLE, _known_revisions


class SchemaOwnershipTests(unittest.TestCase):
    def test_ai_metadata_excludes_suitcase_tables(self):
        self.assertFalse(
            {"suitcase_trip", "suitcase_expense", "suitcase_goal"} & set(Base.metadata.tables)
        )

    def test_ai_uses_a_dedicated_known_migration_chain(self):
        self.assertEqual(VERSION_TABLE, "ai_agent_alembic_version")
        self.assertIn("f7a1b2c3d4e5", _known_revisions())
