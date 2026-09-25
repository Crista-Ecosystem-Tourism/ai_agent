"""Dependency-free checks for the league migration and complete Alembic graph."""

import ast
import unittest
from pathlib import Path


VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"
LEAGUE_REVISION = "f8a9b0c1d2e3"
EXPECTED_LEAGUE_PARENTS = {
    "e6f7a8b9c0d1",
    "s8a9b0c1d2e3",
    "z7f8a9b0c1d",
}


def migration_records():
    records = []
    for path in VERSIONS_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue
        assignments = {}
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
            else:
                continue
            if name in {"revision", "down_revision"}:
                assignments[name] = ast.literal_eval(node.value)
        if "revision" in assignments:
            records.append((assignments["revision"], assignments.get("down_revision")))
    return records


class WeeklyLeagueMigrationStaticTests(unittest.TestCase):
    def test_migration_graph_has_unique_revisions_resolved_parents_and_one_head(self):
        records = migration_records()
        revisions = [revision for revision, _ in records]
        self.assertEqual(len(revisions), len(set(revisions)))
        graph = dict(records)

        referenced = set()
        for parents in graph.values():
            for parent in (parents,) if isinstance(parents, str) else parents or ():
                self.assertIn(parent, graph, f"missing parent revision {parent}")
                referenced.add(parent)

        heads = set(graph) - referenced
        self.assertEqual(1, len(heads))

    def test_league_revision_merges_the_three_existing_heads(self):
        self.assertEqual(EXPECTED_LEAGUE_PARENTS, set(dict(migration_records())[LEAGUE_REVISION]))


if __name__ == "__main__":
    unittest.main()
