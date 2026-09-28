"""publish Moscow Wiki revisions with complete provenance

Revision ID: c50b1c2d3e4
Revises: b40b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c50b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "b40b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LICENSE = "CC BY 4.0"
SOURCE_URL = "https://kreml.ru/"
RIGHTS_URL = "https://kreml.ru/en/services/frequent-questions"
CHECKED_AT = "2026-09-28"
SOURCES = [{
    "label": "Музеи Московского Кремля: официальный сайт",
    "url": SOURCE_URL,
    "source_kind": "official",
    "rights_basis": "public_facts",
    "rights_url": RIGHTS_URL,
    "checked_at": CHECKED_AT,
}]
ENGLISH_SOURCES = [{**SOURCES[0], "label": "Moscow Kremlin Museums: official website"}]
EDITIONS = [
    {
        "article_id": "wiki-moscow",
        "version_id": "wiki-moscow-v2",
        "title": "Москва: Кремль и Красная площадь",
        "body": {
            "summary": "Москва — столица России. Маршрут Crista раскрывает её через Кремль, Красную площадь и конкретные уроки с собственными первоисточниками.",
            "history": "Московский Кремль и Соборная площадь образуют историческое ядро маршрута. Wiki даёт общий контекст, а каждый игровой урок сохраняет отдельную ссылку на факт, по которому строится задание.",
            "route": "Городской путь проходит десять последовательных точек в пяти районах. Он открывает следующую точку только после подтверждённого ответа на предыдущую и не выдаёт локальный прогресс браузера за серверный факт.",
            "practical": [
                {"label": "Перед посещением", "value": "Проверяйте действующие часы, билеты и правила на официальном сайте Музеев Московского Кремля."},
                {"label": "В Crista", "value": "Используйте ссылку под уроком для проверки конкретного факта; Wiki служит только городским контекстом."},
            ],
        },
        "sources": SOURCES,
    },
    {
        "article_id": "wiki-moscow-en",
        "version_id": "wiki-moscow-en-v2",
        "title": "Moscow: the Kremlin and Red Square",
        "body": {
            "summary": "Moscow is Russia’s capital. Crista’s route introduces it through the Kremlin, Red Square and specific lessons with their own primary sources.",
            "history": "The Moscow Kremlin and Cathedral Square form the historic core of the route. The Wiki provides city context, while each game lesson retains a separate factual link for its question.",
            "route": "The city path has ten sequential stops across five districts. It unlocks the next stop only after a confirmed answer to the preceding one and never presents browser-local progress as a server fact.",
            "practical": [
                {"label": "Before visiting", "value": "Check current opening hours, tickets and visitor rules on the Moscow Kremlin Museums’ official website."},
                {"label": "In Crista", "value": "Use the source under each lesson to check its precise fact; the Wiki is city context only."},
            ],
        },
        "sources": ENGLISH_SOURCES,
    },
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    versions = sa.table(
        "wiki_article_version",
        sa.column("id", sa.String()), sa.column("article_id", sa.String()), sa.column("author_id", sa.String()),
        sa.column("status", sa.String()), sa.column("title", sa.String()), sa.column("body", postgresql.JSONB()),
        sa.column("sources", postgresql.JSONB()), sa.column("license", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)), sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(versions, [{
        "id": edition["version_id"], "article_id": edition["article_id"], "author_id": "crista-editorial",
        "status": "published", "title": edition["title"], "body": edition["body"], "sources": edition["sources"],
        "license": LICENSE, "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    } for edition in EDITIONS])
    for edition in EDITIONS:
        op.execute(sa.text(
            "UPDATE wiki_article SET published_version_id = :version_id, updated_at = :now WHERE id = :article_id"
        ).bindparams(version_id=edition["version_id"], article_id=edition["article_id"], now=now))
    op.execute(sa.text("""
        INSERT INTO game_content_revision (id, kind, payload, is_published, published_at, created_at, updated_at)
        SELECT 'moscow-sandbox-activities-v9', kind,
          payload || CAST('{"id":"moscow-sandbox-activities-v9","wiki_reference":{"slug":"moscow","version_id":"wiki-moscow-v2"}}' AS jsonb),
          TRUE, :now, :now, :now
        FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v8'
    """).bindparams(now=now))
    op.execute(sa.text(
        "UPDATE game_city SET sandbox_content_revision_id = 'moscow-sandbox-activities-v9', updated_at = :now WHERE id = 'moscow'"
    ).bindparams(now=now))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-sandbox-activities-v9'"))
    op.execute(sa.text(
        "UPDATE game_city SET sandbox_content_revision_id = 'moscow-sandbox-activities-v8' WHERE id = 'moscow'"
    ))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v9'"))
    for edition in EDITIONS:
        previous_version = "wiki-moscow-v1" if edition["article_id"] == "wiki-moscow" else "wiki-moscow-en-v1"
        op.execute(sa.text(
            "UPDATE wiki_article SET published_version_id = :version_id WHERE id = :article_id"
        ).bindparams(version_id=previous_version, article_id=edition["article_id"]))
        op.execute(sa.text(
            "DELETE FROM wiki_article_version WHERE id = :version_id"
        ).bindparams(version_id=edition["version_id"]))
