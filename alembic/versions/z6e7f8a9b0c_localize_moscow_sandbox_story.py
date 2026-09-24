"""publish an English edition of the Moscow sandbox story card

Revision ID: z6e7f8a9b0c
Revises: z5d6e7f8a9b
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "z6e7f8a9b0c"
down_revision = "z5d6e7f8a9b"
branch_labels = None
depends_on = None

NOW = datetime.now(timezone.utc)
CONTENT_REVISION_ID = "moscow-sandbox-activities-v8"

payload = {
    "story": {
        "title": "Story: Red Square",
        "eyebrow": "Story · 1 of 1",
        "image_alt": "Stylized illustration of Red Square, Saint Basil's Cathedral, and the Kremlin wall in the evening light",
        "media_credit": "Original Crista illustration created for this educational story card",
        "fact": "The square's name is not about its color: in older Russian, krasny meant ‘beautiful.’",
        "source_label": "Moscow City Government · ‘Moscow: What to See’",
        "note": "The illustration sets the scene; check the historical fact against the primary source.",
    },
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
    op.bulk_insert(translations, [{
        "id": "moscow-sandbox-v8-en-v1",
        "content_revision_id": CONTENT_REVISION_ID,
        "language": "en",
        "payload": payload,
        "is_published": True,
        "published_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }])


def downgrade() -> None:
    translations = sa.table("game_content_translation", sa.column("id", sa.String()))
    op.get_bind().execute(
        sa.delete(translations).where(translations.c.id == "moscow-sandbox-v8-en-v1")
    )
