"""Dependency-free structural checks for the country Wiki seed migrations.

These checks do not replace applying the migrations to PostgreSQL. They keep
the Alembic chain and the version/article/source references auditable even in
environments where the database test service is unavailable.
"""
import ast
import unittest
from pathlib import Path


MIGRATION_FILES = (
    "t9b0c1d2e3f4_publish_japan_wiki_article.py",
    "u0c1d2e3f4a_publish_georgia_wiki_article.py",
    "v1d2e3f4a5b_publish_russia_wiki_article.py",
)
COUNTRIES = (
    ("jp", "Япония"),
    ("ge", "Грузия"),
    ("ru", "Россия"),
)


def _literal(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Dict):
        return {
            _literal(key): _literal(value)
            for key, value in zip(node.keys, node.values)
            if isinstance(key, ast.Constant)
        }
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_literal(item) for item in node.elts]
    return None


def _migration_data(path: Path):
    tree = ast.parse(path.read_text())
    assignments = {}
    rows = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments[node.target.id] = _literal(node.value)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            assignments[node.targets[0].id] = _literal(node.value)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "op" or node.func.attr != "bulk_insert":
            continue
        if len(node.args) != 2 or not isinstance(node.args[1], ast.List):
            continue
        rows.extend(_literal(row) for row in node.args[1].elts if isinstance(row, ast.Dict))
    return assignments, rows


class CountryWikiSeedMigrationStaticTests(unittest.TestCase):
    def test_country_versions_form_a_linked_published_chain(self):
        versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
        previous = "s8a9b0c1d2e3"
        seen_revisions = set()

        for (country_code, title), filename in zip(COUNTRIES, MIGRATION_FILES):
            assignments, rows = _migration_data(versions_dir / filename)
            revision = assignments.get("revision")
            self.assertEqual(assignments.get("down_revision"), previous)
            self.assertNotIn(revision, seen_revisions)
            seen_revisions.add(revision)
            previous = revision

            article_id = f"wiki-country-{country_code}"
            version_id = f"{article_id}-v1"
            articles = [row for row in rows if row.get("slug") == f"country-{country_code}"]
            versions = [row for row in rows if row.get("article_id") == article_id]
            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0].get("id"), article_id)
            self.assertEqual(len(versions), 1)
            self.assertEqual(versions[0].get("id"), version_id)
            self.assertEqual(versions[0].get("title"), title)
            self.assertEqual(versions[0].get("status"), "published")
            self.assertEqual(versions[0].get("license"), "CC BY 4.0")
            sources = versions[0].get("sources")
            self.assertGreaterEqual(len(sources), 3)
            self.assertTrue(all(source["url"].startswith("https://") for source in sources))


if __name__ == "__main__":
    unittest.main()
