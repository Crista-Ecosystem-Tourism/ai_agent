"""add immutable English editions for city pilot lessons

Revision ID: x3b4c5d6e7f8
Revises: w2a3b4c5d6e7
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "x3b4c5d6e7f8"
down_revision = "w2a3b4c5d6e7"
branch_labels = None
depends_on = None


def _edition(quest_id, title, fact, source_label, question, options, stamp_title):
    return {
        "id": f"{quest_id}-en-v1",
        "content_revision_id": f"{quest_id}-v1",
        "language": "en",
        "payload": {
            "scene": {"title": title},
            "fact": {"text": fact, "source_label": source_label},
            "question": {"text": question, "options": [{"id": key, "label": label} for key, label in options]},
            "reward": {"stamp_title": stamp_title},
        },
        "is_published": True,
        "published_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }


NOW = datetime.now(timezone.utc)


def upgrade() -> None:
    op.create_table(
        "game_content_translation",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("content_revision_id", sa.String(), sa.ForeignKey("game_content_revision.id"), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("content_revision_id", "language", name="uq_game_content_translation_locale"),
    )
    op.create_index(
        "idx_game_content_translation_published",
        "game_content_translation",
        ["content_revision_id", "language", "is_published"],
    )

    translations = sa.table(
        "game_content_translation",
        sa.column("id", sa.String()), sa.column("content_revision_id", sa.String()),
        sa.column("language", sa.String()), sa.column("payload", postgresql.JSONB()),
        sa.column("is_published", sa.Boolean()), sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    entries = [
        ("spb-hermitage", "The Hermitage", "The Hermitage dates the museum's founding to 1764, when Catherine the Great acquired Johann Ernst Gotzkowsky's collection.", "The State Hermitage Museum", "In what year was the Hermitage founded?", [("1703", "1703"), ("1764", "1764"), ("1917", "1917")], "Hermitage Stamp"),
        ("spb-peterhof", "Peterhof", "Peterhof was ceremonially opened on 15 August 1723.", "Peterhof State Museum Reserve", "Choose the year Peterhof was ceremonially opened.", [("1714", "1714"), ("1723", "1723"), ("1762", "1762")], "Peterhof Stamp"),
        ("spb-collection", "The Hermitage Collection", "The State Hermitage Museum collection contains more than three million works of art and artifacts from world cultures.", "The State Hermitage Museum", "How many works of art and artifacts are in the Hermitage collection?", [("Около 300 тыс.", "About 300,000"), ("Более 3 млн", "More than 3 million"), ("Более 30 млн", "More than 30 million")], "Hermitage Collection Stamp"),
        ("spb-fountains", "Peterhof Fountains", "Peterhof's parks contain four cascades and more than 150 fountains.", "Peterhof State Museum Reserve", "How many fountains are in Peterhof's parks?", [("Около 15", "About 15"), ("Свыше 150", "More than 150"), ("Свыше 1 500", "More than 1,500")], "Peterhof Fountains Stamp"),
        ("spb-peterhof-history", "The First Mention of Peterhof", "The first documented mention of Peterhof in Peter the Great's campaign journal dates to 1705.", "Peterhof State Museum Reserve", "Is it true that Peterhof was first documented in 1705?", [("fact", "True"), ("myth", "False")], "Peterhof History Stamp"),
        ("sochi-national-park", "Sochi National Park", "Founded on 5 May 1983, Sochi National Park was the first national park in Russia.", "Sochi National Park", "In what year was Sochi National Park founded?", [("1973", "1973"), ("1983", "1983"), ("1993", "1993")], "Sochi National Park Stamp"),
        ("sochi-dendrarium", "Sochi Arboretum", "The main planting work at Sochi Arboretum was completed in 1892.", "Sochi National Park", "Choose the year the main planting work at Sochi Arboretum was completed.", [("1882", "1882"), ("1892", "1892"), ("1902", "1902")], "Sochi Arboretum Stamp"),
        ("sochi-forest", "Mountain Forests", "Mountain forests cover 94.1% of Sochi National Park.", "Sochi National Park", "What share of the park is covered by mountain forests?", [("49,1%", "49.1%"), ("74,1%", "74.1%"), ("94,1%", "94.1%")], "Mountain Forests Stamp"),
        ("sochi-mzymta", "The Mzymta River", "The Mzymta is the largest river in the park and runs for 89 km within its territory.", "Sochi National Park", "How long is the Mzymta within the park?", [("29 км", "29 km"), ("89 км", "89 km"), ("189 км", "189 km")], "Mzymta River Stamp"),
        ("sochi-park-area", "The National Park's Area", "Sochi National Park covers 214,098.6 hectares.", "Sochi National Park", "Is it true that Sochi National Park covers 214,098.6 hectares?", [("fact", "True"), ("myth", "False")], "National Park Area Stamp"),
    ]
    op.bulk_insert(translations, [_edition(*entry) for entry in entries])


def downgrade() -> None:
    op.drop_index("idx_game_content_translation_published", table_name="game_content_translation")
    op.drop_table("game_content_translation")
