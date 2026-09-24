"""Public Wiki article endpoint contract tests without a database."""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.wiki import router
from app.dependencies import get_wiki_service
from app.services.wiki import WikiNotFoundError


PUBLISHED_ARTICLE = {
    "version_id": "wiki-country-jp-v1",
    "slug": "country-jp",
    "title": "Япония",
    "body": {"summary": "Опубликованная версия."},
    "sources": [{"label": "Источник", "url": "https://example.test/japan"}],
    "license": "CC BY 4.0",
    "published_at": "2026-09-24T00:00:00+00:00",
    "content_language": "ru",
}


class StubWikiService:
    async def get_published(self, slug, language="ru"):
        if slug != PUBLISHED_ARTICLE["slug"]:
            raise WikiNotFoundError(slug)
        return {**PUBLISHED_ARTICLE, "content_language": language}


def create_test_app():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_wiki_service] = StubWikiService
    return app


class WikiPublicArticleEndpointTests(unittest.TestCase):
    def test_published_article_is_available_without_authentication(self):
        with TestClient(create_test_app()) as client:
            response = client.get("/wiki/articles/country-jp")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), PUBLISHED_ARTICLE)

    def test_missing_publication_returns_not_found(self):
        with TestClient(create_test_app()) as client:
            response = client.get("/wiki/articles/country-ge")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Опубликованная статья не найдена")

    def test_language_is_forwarded_and_reported(self):
        with TestClient(create_test_app()) as client:
            response = client.get("/wiki/articles/country-jp?language=en")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content_language"], "en")


if __name__ == "__main__":
    unittest.main()
