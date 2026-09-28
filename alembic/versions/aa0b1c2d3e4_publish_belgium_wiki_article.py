"""publish the Belgium country Wiki article

Revision ID: aa0b1c2d3e4
Revises: z9a0b1c2d3e4
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "aa0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "z9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTICLE_ID = "wiki-country-be"
VERSION_ID = "wiki-country-be-v1"
AUTHOR_ID = "crista-editorial"

BODY = {
    "summary": "Бельгия соединяет несколько языковых и региональных традиций; Брюссель и Брюгге в каталоге Crista дают разные входы в эту историю.",
    "history": "Брюссельская Гран-Плас возникла как рыночная площадь в XII веке. Ратуша в готическом стиле строилась в XV веке, а окружающие её дома связаны с городскими гильдиями. После бомбардировки 1695 года площадь почти полностью отстроили заново; ЮНЕСКО описывает ансамбль как важный политический и торговый центр, отражённый в архитектуре конца XVII века.",
    "cuisine": "У Брюсселя есть собственные гастрономические особенности: брюссельская вафля лёгкая, прямоугольная и обычно несладкая, а начинка или посыпка добавляются при подаче. Visit Brussels также связывает с городом шоколад, пиво, спекулос и другие бельгийские специалитеты. Рецепты и привычки различаются между регионами.",
    "traditions": "В Бельгии три национальных языка — нидерландский, французский и немецкий. Язык вывески и повседневного общения зависит от региона; в Брюсселе полезно обращать внимание на языковой вариант указателей и сервисной информации.",
    "practical": [
        {"label": "Валюта", "value": "Евро (EUR)"},
        {"label": "Экстренная помощь", "value": "112 · пожарная служба, скорая и полиция; 101 · срочная помощь полиции"},
    ],
}

SOURCES = [
    {"label": "Visit Brussels: история Гран-Плас", "url": "https://www.visit.brussels/en/visitors/plan-your-trip/a-legendary-stay-for-history-buffs/day-1-exploring-the-historical-centre"},
    {"label": "ЮНЕСКО: Гран-Плас, Брюссель", "url": "https://whc.unesco.org/en/list/857"},
    {"label": "Visit Brussels: кулинарные особенности города", "url": "https://www.visit.brussels/en/visitors/where-to-eat/bruxelles-et-ses-specialites-culinaires"},
    {"label": "Belgium.be: кратко о Бельгии", "url": "https://www.belgium.be/fr/la_belgique/connaitre_le_pays/la_belgique_en_bref/fiche_belgique"},
    {"label": "112 Belgium: как вызвать помощь", "url": "https://112.be/en/how-call/how-call-112"},
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": ARTICLE_ID, "slug": "country-be", "published_version_id": None,
        "created_at": now, "updated_at": now,
    }])
    op.bulk_insert(sa.table(
        "wiki_article_version",
        sa.column("id", sa.String()), sa.column("article_id", sa.String()), sa.column("author_id", sa.String()),
        sa.column("status", sa.String()), sa.column("title", sa.String()), sa.column("body", postgresql.JSONB()),
        sa.column("sources", postgresql.JSONB()), sa.column("license", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)), sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": VERSION_ID, "article_id": ARTICLE_ID, "author_id": AUTHOR_ID,
        "status": "published", "title": "Бельгия", "body": BODY, "sources": SOURCES,
        "license": "CC BY 4.0", "reviewed_at": now, "published_at": now,
        "created_at": now, "updated_at": now,
    }])
    op.execute(sa.text(
        "UPDATE wiki_article SET published_version_id = :version_id WHERE id = :article_id"
    ).bindparams(version_id=VERSION_ID, article_id=ARTICLE_ID))


def downgrade() -> None:
    op.execute(sa.text(
        "UPDATE wiki_article SET published_version_id = NULL WHERE id = :article_id"
    ).bindparams(article_id=ARTICLE_ID))
    op.execute(sa.text(
        "DELETE FROM wiki_article_version WHERE id = :version_id"
    ).bindparams(version_id=VERSION_ID))
    op.execute(sa.text(
        "DELETE FROM wiki_article WHERE id = :article_id"
    ).bindparams(article_id=ARTICLE_ID))
