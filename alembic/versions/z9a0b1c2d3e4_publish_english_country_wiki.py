"""publish English editions of the Russia, Japan, and Georgia Wiki pages

Revision ID: z9a0b1c2d3e4
Revises: z8f9a0b1c2d3
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "z9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "z8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LICENSE = "CC BY 4.0"
EDITIONS = [
    {
        "country": "ru", "title": "Russia",
        "body": {
            "summary": "Russia spans many regions and peoples, so cultural traditions and everyday food vary considerably from place to place.",
            "history": "Moscow’s history can be traced through the Kremlin ensemble: the city was first mentioned in writing in 1147, while most of the Kremlin’s brick walls and towers date to its rebuilding between 1485 and 1495.",
            "cuisine": "Regional cuisines use different ingredients and recipes. Central Russia is known for shchi, porridge, and baked goods; traditions of the many peoples of the Volga region have shaped its food, while southern cooking uses its own vegetables and seasonings.",
            "traditions": "People in Russia have many languages, crafts, holidays, and customs. Regional context matters: no single tradition or dish represents the whole country.",
            "practical": [
                {"label": "Currency", "value": "Russian ruble (₽)"},
                {"label": "Unified emergency number", "value": "112"},
            ],
        },
        "sources": [
            {"label": "Moscow Kremlin Museums: history of the ensemble", "url": "https://kremlin-architectural-ensemble.kreml.ru/en-Us/history/view/"},
            {"label": "Culture.ru: regional cuisines of Russia", "url": "https://www.culture.ru/materials/254771/kukhni-rossii-tradicionnye-blyuda-i-ikh-istoriya"},
            {"label": "Culture.ru: peoples of Russia", "url": "https://www.culture.ru/s/narody-rossii/"},
            {"label": "Bank of Russia: cash circulation", "url": "https://www.cbr.ru/eng/cash_circulation/"},
            {"label": "EMERCOM of Russia: calling emergency services", "url": "https://mchs.gov.ru/deyatelnost/bezopasnost-grazhdan/kak-pravilno-vyzvat-skoruyu_5"},
        ],
    },
    {
        "country": "jp", "title": "Japan",
        "body": {
            "summary": "Japan has diverse regional cultures; learning about its history and everyday customs helps visitors understand places in greater context.",
            "history": "During the Edo period (1603–1867), urban culture flourished, including kabuki theatre and ukiyo-e prints. The Meiji Restoration began in 1868 and brought far-reaching modernization.",
            "cuisine": "Washoku, Japan’s traditional food culture, was inscribed on UNESCO’s Intangible Cultural Heritage list in 2013. It emphasizes seasonality, a variety of local ingredients, and regional differences.",
            "traditions": "Customs vary by region and setting. Guests may be asked to remove their shoes at homes and some establishments; at the table, it is helpful to follow the way a particular meal is served.",
            "practical": [
                {"label": "Currency", "value": "Japanese yen (JPY, ¥)"},
                {"label": "Police · emergency", "value": "110"},
                {"label": "Fire service / ambulance · emergency", "value": "119"},
            ],
        },
        "sources": [
            {"label": "JNTO: overview of Japanese history", "url": "https://www.japan.travel/en/responsible-travel-guide/features/overview-japanese-history/"},
            {"label": "MAFF: what is washoku?", "url": "https://www.maff.go.jp/e/policies/market/washoku-world-challenge/en/learning_01.html"},
            {"label": "JNTO: currency and exchange", "url": "https://www.japan.travel/en/plan/currency/"},
            {"label": "JNTO: emergency hotlines", "url": "https://www.japan.travel/en/plan/hotline/"},
        ],
    },
    {
        "country": "ge", "title": "Georgia",
        "body": {
            "summary": "Georgia is a Caucasus country with diverse regional cuisines and living traditions shaped by local communities.",
            "history": "The kingdom of Iberia developed in what is now eastern Georgia in the fourth century BCE. Several Georgian states united in the early eleventh century; the country’s history has unfolded at the crossroads of regional cultures and political influences.",
            "cuisine": "Georgian cuisine varies markedly by region. Khinkali and khachapuri are widely known dishes, and khachapuri has many regional forms. The traditional Georgian winemaking method in qvevri is inscribed on UNESCO’s Representative List of the Intangible Cultural Heritage of Humanity.",
            "traditions": "Feasting customs and recipes differ across regions. Families and communities sustain qvevri winemaking, passing knowledge of the clay vessels and the process between generations.",
            "practical": [
                {"label": "Currency", "value": "Georgian lari (GEL)"},
                {"label": "Emergency number", "value": "112 · police, fire, and ambulance"},
            ],
        },
        "sources": [
            {"label": "Georgia Travel: history of Georgia", "url": "https://georgia.travel/why-georgia-history"},
            {"label": "Georgia Travel: Georgian cuisine", "url": "https://georgia.travel/georgian-cuisine"},
            {"label": "UNESCO: traditional Georgian winemaking in qvevri", "url": "https://ich.unesco.org/en/decisions/8.COM/8.13"},
            {"label": "Georgia Travel: currency", "url": "https://georgia.travel/coming-to-georgia/currency"},
            {"label": "112 Georgia: when to call", "url": "https://112.gov.ge/?lang=en&page_id=1686"},
        ],
    },
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(sa.table(
        "wiki_article",
        sa.column("id", sa.String()), sa.column("slug", sa.String()),
        sa.column("published_version_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": f"wiki-country-{edition['country']}-en",
        "slug": f"country-{edition['country']}-en",
        "published_version_id": None, "created_at": now, "updated_at": now,
    } for edition in EDITIONS])
    op.bulk_insert(sa.table(
        "wiki_article_version",
        sa.column("id", sa.String()), sa.column("article_id", sa.String()), sa.column("author_id", sa.String()),
        sa.column("status", sa.String()), sa.column("title", sa.String()), sa.column("body", postgresql.JSONB()),
        sa.column("sources", postgresql.JSONB()), sa.column("license", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)), sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    ), [{
        "id": f"wiki-country-{edition['country']}-en-v1",
        "article_id": f"wiki-country-{edition['country']}-en",
        "author_id": "crista-editorial", "status": "published", "title": edition["title"],
        "body": edition["body"], "sources": edition["sources"], "license": LICENSE,
        "reviewed_at": now, "published_at": now, "created_at": now, "updated_at": now,
    } for edition in EDITIONS])
    for edition in EDITIONS:
        op.execute(sa.text(
            "UPDATE wiki_article SET published_version_id = :version_id WHERE id = :article_id"
        ).bindparams(
            version_id=f"wiki-country-{edition['country']}-en-v1",
            article_id=f"wiki-country-{edition['country']}-en",
        ))


def downgrade() -> None:
    for edition in EDITIONS:
        article_id = f"wiki-country-{edition['country']}-en"
        op.execute(sa.text(
            "UPDATE wiki_article SET published_version_id = NULL WHERE id = :article_id"
        ).bindparams(article_id=article_id))
        op.execute(sa.text(
            "DELETE FROM wiki_article_version WHERE id = :version_id"
        ).bindparams(version_id=f"wiki-country-{edition['country']}-en-v1"))
        op.execute(sa.text(
            "DELETE FROM wiki_article WHERE id = :article_id"
        ).bindparams(article_id=article_id))
