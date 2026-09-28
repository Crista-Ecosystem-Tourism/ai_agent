"""publish sourced Saint Petersburg Wiki editions

Revision ID: b40b1c2d3e4
Revises: b30b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b40b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "b30b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LICENSE = "CC BY 4.0"
RIGHTS_URL = "https://www.deti.peterhofmuseum.ru/about/docs"
CHECKED_AT = "2026-09-28"
SOURCES = [
    {
        "label": "ГМЗ «Петергоф»: история Петергофа",
        "url": "https://peterhofmuseum.ru/objects/peterhof",
        "source_kind": "official",
        "rights_basis": "public_facts",
        "rights_url": RIGHTS_URL,
        "checked_at": CHECKED_AT,
    },
    {
        "label": "ГМЗ «Петергоф»: фонтаны Нижнего парка и Верхнего сада",
        "url": "https://go.peterhofmuseum.ru/info/fountains/",
        "source_kind": "official",
        "rights_basis": "public_facts",
        "rights_url": RIGHTS_URL,
        "checked_at": CHECKED_AT,
    },
]
ENGLISH_SOURCES = [
    {**source, "label": label}
    for source, label in zip(SOURCES, (
        "Peterhof State Museum-Reserve: Peterhof history",
        "Peterhof State Museum-Reserve: fountains in the Lower Park and Upper Garden",
    ))
]
EDITIONS = [
    {
        "article_id": "wiki-st-petersburg",
        "slug": "st-petersburg",
        "version_id": "wiki-st-petersburg-v1",
        "title": "Санкт-Петербург: Эрмитаж и Петергоф",
        "body": {
            "summary": "Пилотный маршрут Crista по Санкт-Петербургу соединяет Эрмитаж и Петергоф. Он предлагает сверять игровые факты с официальными страницами музеев, а не заменять ими самостоятельное исследование города.",
            "history": "Петергофский маршрут опирается на историю ансамбля: первое документальное упоминание относится к 1705 году, строительство резиденции началось в 1714 году, а торжественное открытие состоялось 15 августа 1723 года. Уроки Эрмитажа сохраняют собственные первоисточники для фактов о музее и его коллекции.",
            "culture": "Петергоф создавался как дворцово-парковый ансамбль. Его история связывает архитектуру, сады и гидротехническую систему фонтанов; поэтому маршрут читает город через конкретные музейные объекты, а не через обобщённый образ Санкт-Петербурга.",
            "route": "В Нижнем парке и Верхнем саду Петергофа четыре каскада и более 150 фонтанов. Их работа основана на самотёчной системе водовода без насосов; этот факт можно проверить на официальной странице музея.",
            "practical": [
                {"label": "Перед посещением", "value": "Проверяйте актуальные часы работы, билеты и правила на официальном сайте музея."},
                {"label": "В маршруте Crista", "value": "Открывайте первоисточник под каждым уроком: Wiki даёт контекст, а урок сохраняет точную ссылку на факт."},
            ],
        },
        "sources": SOURCES,
    },
    {
        "article_id": "wiki-st-petersburg-en",
        "slug": "st-petersburg-en",
        "version_id": "wiki-st-petersburg-en-v1",
        "title": "Saint Petersburg: the Hermitage and Peterhof",
        "body": {
            "summary": "Crista’s Saint Petersburg pilot connects the Hermitage and Peterhof. It invites players to check game facts against the museums’ official pages rather than treating the route as a substitute for exploring the city independently.",
            "history": "The Peterhof part of the route follows the ensemble’s history: the first documented record dates to 1705, construction of the residence began in 1714, and the ceremonial opening took place on 15 August 1723. Hermitage lessons retain their own primary sources for facts about the museum and its collection.",
            "culture": "Peterhof was created as a palace and park ensemble. Its history connects architecture, gardens and a fountain water system, so the route approaches the city through specific museum sites instead of a single general image of Saint Petersburg.",
            "route": "Peterhof’s Lower Park and Upper Garden contain four cascades and more than 150 fountains. They operate through a gravity-fed water system without pumps; the museum’s official guide documents this fact.",
            "practical": [
                {"label": "Before visiting", "value": "Check current opening hours, tickets and visitor rules on the museum’s official website."},
                {"label": "In the Crista route", "value": "Open the primary source under each lesson: the Wiki provides context, while the lesson preserves its precise factual link."},
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
