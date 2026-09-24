"""add a published English edition of the Moscow city boss

Revision ID: z5d6e7f8a9b
Revises: y4c5d6e7f8a
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "z5d6e7f8a9b"
down_revision = "y4c5d6e7f8a"
branch_labels = None
depends_on = None

NOW = datetime.now(timezone.utc)
CONTENT_REVISION_ID = "moscow-city-boss-v1"

payload = {
    "chris": {
        "name": "Chris",
        "intro": "You completed the city loop. Bring three facts together into one story of Moscow—and earn the city stamp.",
    },
    "scene": {"title": "Moscow Final Round"},
    "questions": [
        {
            "id": "moscow-boss-cathedral",
            "text": "In what year was the Cathedral of the Annunciation consecrated?",
            "options": [("1489", "1489"), ("1561", "1561"), ("1613", "1613")],
            "explanation": "The cathedral was built from 1484 to 1489 and consecrated in 1489.",
        },
        {
            "id": "moscow-boss-gum",
            "text": "In what year did the Upper Trading Rows, now GUM, open?",
            "options": [("1825", "1825"), ("1893", "1893"), ("1939", "1939")],
            "explanation": "The Upper Trading Rows opened on 2 December 1893.",
        },
        {
            "id": "moscow-boss-vdnh",
            "text": "In what year did the first exhibition at VDNKh open?",
            "options": [("1923", "1923"), ("1939", "1939"), ("1959", "1959")],
            "explanation": "VDNKh's history began with the exhibition that opened on 1 August 1939.",
        },
    ],
    "sources": [
        {"label": "Moscow Kremlin Museums", "url": "https://annunciation-cathedral.kreml.ru/history/view/"},
        {"label": "GUM", "url": "https://gum.ru/history/"},
        {"label": "VDNKh", "url": "https://vdnh.ru/visitors/about/"},
    ],
}


def _translation_row():
    localized_questions = []
    for question in payload["questions"]:
        localized_questions.append({
            "id": question["id"],
            "text": question["text"],
            "options": [{"id": key, "label": label} for key, label in question["options"]],
            "explanation": question["explanation"],
        })
    localized_payload = {
        "chris": payload["chris"],
        "scene": payload["scene"],
        "questions": localized_questions,
        "sources": payload["sources"],
    }
    return {
        "id": "moscow-city-boss-en-v1",
        "content_revision_id": CONTENT_REVISION_ID,
        "language": "en",
        "payload": localized_payload,
        "is_published": True,
        "published_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }


def upgrade() -> None:
    translations = sa.table(
        "game_content_translation",
        sa.column("id", sa.String()),
        sa.column("content_revision_id", sa.String()),
        sa.column("language", sa.String()),
        sa.column("payload", postgresql.JSONB()),
        sa.column("is_published", sa.Boolean()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(translations, [_translation_row()])


def downgrade() -> None:
    translations = sa.table("game_content_translation", sa.column("id", sa.String()))
    op.get_bind().execute(
        sa.delete(translations).where(translations.c.id == "moscow-city-boss-en-v1")
    )
