"""publish sourced Sochi Wiki editions

Revision ID: d60b1c2d3e4
Revises: c50b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d60b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "c50b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LICENSE = "CC BY 4.0"
SOURCE_URL = "https://npsochi.ru/about/"
CHECKED_AT = "2026-09-28"
SOURCES = [{
    "label": "Сочинский национальный парк: официальный справочник",
    "url": SOURCE_URL,
    "source_kind": "official",
    "rights_basis": "public_facts",
    "rights_url": SOURCE_URL,
    "checked_at": CHECKED_AT,
}]
ENGLISH_SOURCES = [{**SOURCES[0], "label": "Sochi National Park: official overview"}]
EDITIONS = [
    {
        "article_id": "wiki-sochi",
        "slug": "sochi",
        "version_id": "wiki-sochi-v1",
        "title": "Сочи: национальный парк и Дендрарий",
        "body": {
            "summary": "Городской маршрут Crista по Сочи начинается с национального парка и Дендрария. Wiki даёт проверяемый контекст к урокам и сохраняет ссылку на официальный источник, а не заменяет подготовку к поездке.",
            "history": "Сочинский национальный парк основан 5 мая 1983 года и считается первым национальным парком России. Его территория проходит вдоль черноморского побережья Большого Сочи на северо-западе Большого Кавказа.",
            "culture": "В границах парка встречаются водопады, пещеры, ущелья, каньоны, высокогорные озёра и минеральные источники. Дендрарий выделяется как исторический садово-парковый объект с коллекцией древесной флоры пяти континентов.",
            "route": "Площадь парка составляет 214 098,6 га, а горные леса занимают 94,1% территории. Самая крупная река в парке — Мзымта, её протяжённость здесь составляет 89 км. Эти факты вынесены в отдельные уроки с первоисточником.",
            "practical": [
                {"label": "Перед посещением", "value": "Проверяйте правила посещения, маршруты и билеты на официальном сайте Сочинского национального парка."},
                {"label": "В маршруте Crista", "value": "Открывайте источник под уроком для проверки точного факта; Wiki служит контекстом городского пути."},
            ],
        },
        "sources": SOURCES,
    },
    {
        "article_id": "wiki-sochi-en",
        "slug": "sochi-en",
        "version_id": "wiki-sochi-en-v1",
        "title": "Sochi: the National Park and Arboretum",
        "body": {
            "summary": "Crista’s Sochi city route begins with the national park and the Arboretum. This Wiki provides verifiable context for the lessons and retains the official source link; it does not replace planning a visit.",
            "history": "Sochi National Park was founded on 5 May 1983 and is described as Russia’s first national park. Its territory follows the Black Sea coast of Greater Sochi in the north-western Greater Caucasus.",
            "culture": "The park includes waterfalls, caves, gorges, canyons, high-mountain lakes and mineral springs. The Arboretum is a historic garden-and-park site with a woody-plant collection from five continents.",
            "route": "The park covers 214,098.6 hectares, and mountain forests occupy 94.1 percent of its territory. The Mzymta is its largest river and runs for 89 km inside the park. Separate lessons retain the primary source for these facts.",
            "practical": [
                {"label": "Before visiting", "value": "Check visitor rules, routes and tickets on Sochi National Park’s official website."},
                {"label": "In the Crista route", "value": "Open the source under a lesson to verify its exact fact; the Wiki provides city-path context."},
            ],
        },
        "sources": ENGLISH_SOURCES,
    },
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    articles = sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    versions = sa.table(
        "wiki_article_version",
        sa.column("id", sa.String()), sa.column("article_id", sa.String()), sa.column("author_id", sa.String()),
        sa.column("status", sa.String()), sa.column("title", sa.String()), sa.column("body", postgresql.JSONB()),
        sa.column("sources", postgresql.JSONB()), sa.column("license", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)), sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(articles, [{
        "id": edition["article_id"], "slug": edition["slug"], "published_version_id": None,
        "created_at": now, "updated_at": now,
    } for edition in EDITIONS])
    op.bulk_insert(versions, [{
        "id": edition["version_id"], "article_id": edition["article_id"], "author_id": "crista-editorial",
        "status": "published", "title": edition["title"], "body": edition["body"], "sources": edition["sources"],
        "license": LICENSE, "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    } for edition in EDITIONS])
    for edition in EDITIONS:
        op.execute(sa.text(
            "UPDATE wiki_article SET published_version_id = :version_id WHERE id = :article_id"
        ).bindparams(version_id=edition["version_id"], article_id=edition["article_id"]))


def downgrade() -> None:
    for edition in EDITIONS:
        op.execute(sa.text(
            "UPDATE wiki_article SET published_version_id = NULL WHERE id = :article_id"
        ).bindparams(article_id=edition["article_id"]))
        op.execute(sa.text(
            "DELETE FROM wiki_article_version WHERE id = :version_id"
        ).bindparams(version_id=edition["version_id"]))
        op.execute(sa.text(
            "DELETE FROM wiki_article WHERE id = :article_id"
        ).bindparams(article_id=edition["article_id"]))
