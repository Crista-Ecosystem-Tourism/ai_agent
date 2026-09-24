"""add published English editions for the Moscow route lessons

Revision ID: y4c5d6e7f8a
Revises: x3b4c5d6e7f8
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "y4c5d6e7f8a"
down_revision = "x3b4c5d6e7f8"
branch_labels = None
depends_on = None

NOW = datetime.now(timezone.utc)


def _edition(entry):
    quest_id = entry["quest_id"]
    return {
        "id": f"{quest_id}-en-v1",
        "content_revision_id": entry["content_revision_id"],
        "language": "en",
        "payload": {
            "scene": {"title": entry["title"]},
            "chris": {"name": "Chris", "intro": entry["intro"]},
            "fact": {"text": entry["fact"], "source_label": entry["source_label"]},
            "question": {
                "text": entry["question"],
                "options": [{"id": key, "label": label} for key, label in entry["options"]],
            },
            "reward": {"stamp_title": entry["stamp_title"]},
        },
        "is_published": True,
        "published_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }


entries = [
    {
        "quest_id": "moscow-red-square",
        "content_revision_id": "onboarding-moscow-v1",
        "title": "Red Square",
        "intro": "Hi, I'm Chris. Let's start our mini-journey through Moscow here.",
        "fact": "The square's name is not about its color: in older Russian, krasny meant ‘beautiful.’",
        "source_label": "Moscow City Government",
        "question": "What did the word krasny mean in the square's old name?",
        "options": [("color", "A color"), ("beautiful", "Beautiful"), ("military", "Military")],
        "stamp_title": "Moscow Starter Stamp",
    },
    {
        "quest_id": "moscow-spasskaya-tower",
        "content_revision_id": "moscow-spasskaya-v1",
        "title": "Spasskaya Tower",
        "intro": "Now that Red Square is behind us, look up at one of the Kremlin's main gateways.",
        "fact": "The Spasskaya Tower of the Moscow Kremlin was built by architect Pietro Antonio Solari in 1491.",
        "source_label": "Moscow Kremlin Museums",
        "question": "In what year was the Spasskaya Tower built?",
        "options": [("1491", "1491"), ("1547", "1547"), ("1812", "1812")],
        "stamp_title": "Spasskaya Tower Stamp",
    },
    {
        "quest_id": "moscow-tsar-bell",
        "content_revision_id": "moscow-tsar-bell-v1",
        "title": "Tsar Bell",
        "intro": "Beyond the Spasskaya Tower, the Kremlin holds the story of the world's largest bell.",
        "fact": "Commissioned by Empress Anna Ioannovna, the Tsar Bell was cast in 1735. It is the world's largest bell, but it has never rung.",
        "source_label": "Moscow Kremlin Museums",
        "question": "In what year was the Tsar Bell cast?",
        "options": [("1613", "1613"), ("1735", "1735"), ("1836", "1836")],
        "stamp_title": "Tsar Bell Stamp",
    },
    {
        "quest_id": "moscow-annunciation-cathedral",
        "content_revision_id": "moscow-annunciation-cathedral-v1",
        "title": "Cathedral of the Annunciation",
        "intro": "Cathedral Square preserves a remarkable example of Russian architecture from the age of Ivan III.",
        "fact": "The Cathedral of the Annunciation was built from 1484 to 1489 and consecrated in 1489.",
        "source_label": "Moscow Kremlin Museums",
        "question": "In what year was the Cathedral of the Annunciation consecrated?",
        "options": [("1489", "1489"), ("1561", "1561"), ("1613", "1613")],
        "stamp_title": "Annunciation Cathedral Stamp",
    },
    {
        "quest_id": "moscow-gum",
        "content_revision_id": "moscow-gum-v1",
        "title": "GUM",
        "intro": "From the Kremlin walls, continue to the historic trading rows beside Red Square.",
        "fact": "The Upper Trading Rows, now known as GUM, opened on 2 December 1893.",
        "source_label": "GUM",
        "question": "In what year did the Upper Trading Rows open?",
        "options": [("1825", "1825"), ("1893", "1893"), ("1939", "1939")],
        "stamp_title": "GUM Stamp",
    },
    {
        "quest_id": "moscow-zaryadye",
        "content_revision_id": "moscow-zaryadye-v1",
        "title": "Zaryadye Park",
        "intro": "Beyond the trading rows, Moscow's historic center meets a modern landscape park.",
        "fact": "Zaryadye, a landscape park beside the Kremlin, opened in 2017.",
        "source_label": "Moscow Urban Development Complex",
        "question": "In what year did Zaryadye Park open?",
        "options": [("1997", "1997"), ("2012", "2012"), ("2017", "2017")],
        "stamp_title": "Zaryadye Stamp",
    },
    {
        "quest_id": "moscow-tretyakov-gallery",
        "content_revision_id": "moscow-tretyakov-gallery-v1",
        "title": "The Tretyakov Gallery",
        "intro": "Cross the river into Zamoskvorechye and the story of Russia's national art collection.",
        "fact": "The Tretyakov Gallery dates its founding to 1856, when Pavel Tretyakov acquired his first painting by a Russian artist.",
        "source_label": "The Tretyakov Gallery",
        "question": "Which year is considered the founding year of the Tretyakov Gallery?",
        "options": [("1812", "1812"), ("1856", "1856"), ("1918", "1918")],
        "stamp_title": "Tretyakov Gallery Stamp",
    },
    {
        "quest_id": "moscow-bolshoi-theatre",
        "content_revision_id": "moscow-bolshoi-theatre-v1",
        "title": "The Bolshoi Theatre",
        "intro": "At Theatre Square, the route moves from a private collection to the city's leading stage.",
        "fact": "The Bolshoi Theatre opened in 1825 after Theatre Square was redesigned.",
        "source_label": "Discover Moscow",
        "question": "In what year did the Bolshoi Theatre open?",
        "options": [("1780", "1780"), ("1825", "1825"), ("1853", "1853")],
        "stamp_title": "Bolshoi Theatre Stamp",
    },
    {
        "quest_id": "moscow-metro",
        "content_revision_id": "moscow-metro-v1",
        "title": "The Moscow Metro",
        "intro": "Next, discover the city underground: the first line connected the center with new districts.",
        "fact": "The first section of the Moscow Metro opened on 15 May 1935.",
        "source_label": "Moscow Metro",
        "question": "In what year did the first section of the Moscow Metro open?",
        "options": [("1917", "1917"), ("1935", "1935"), ("1954", "1954")],
        "stamp_title": "Moscow Metro Stamp",
    },
    {
        "quest_id": "moscow-vdnh",
        "content_revision_id": "moscow-vdnh-v1",
        "title": "VDNKh",
        "intro": "The final stop in the main loop leads to Moscow's exhibition city in the northeast.",
        "fact": "The All-Union Agricultural Exhibition, which marked the beginning of VDNKh, opened on 1 August 1939.",
        "source_label": "VDNKh",
        "question": "In what year did the first exhibition at VDNKh open?",
        "options": [("1923", "1923"), ("1939", "1939"), ("1959", "1959")],
        "stamp_title": "VDNKh Stamp",
    },
]


def upgrade() -> None:
    translations = sa.table(
        "game_content_translation",
        sa.column("id", sa.String()), sa.column("content_revision_id", sa.String()),
        sa.column("language", sa.String()), sa.column("payload", postgresql.JSONB()),
        sa.column("is_published", sa.Boolean()), sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(translations, [_edition(entry) for entry in entries])


def downgrade() -> None:
    translation_ids = [f"{entry['quest_id']}-en-v1" for entry in entries]
    translations = sa.table("game_content_translation", sa.column("id", sa.String()))
    op.get_bind().execute(sa.delete(translations).where(translations.c.id.in_(translation_ids)))
