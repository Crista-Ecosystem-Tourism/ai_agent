"""publish English text for Moscow sandbox exercises

Revision ID: z7f8a9b0c1d
Revises: z6e7f8a9b0c
"""
import json

from alembic import op
import sqlalchemy as sa


revision = "z7f8a9b0c1d"
down_revision = "z6e7f8a9b0c"
branch_labels = None
depends_on = None

CONTENT_REVISION_ID = "moscow-sandbox-activities-v8"
TRANSLATION_ID = "moscow-sandbox-v8-en-v1"

activity_payload = {
    "truth_myth": {
        "title": "True or Myth",
        "intro": "Swipe left for myth or right for truth. The buttons below work the same way and are keyboard accessible.",
        "statements": [
            {"id": "zaryadye-2017", "text": "Zaryadye Park opened in 2017.", "explanation": "True: the landscape park beside the Kremlin opened in 2017."},
            {"id": "metro-1954", "text": "The first section of the Moscow Metro opened in 1954.", "explanation": "Myth: the first section of the Moscow Metro opened on 15 May 1935."},
            {"id": "gum-1893", "text": "The Upper Trading Rows, now GUM, opened in 1893.", "explanation": "True: the Upper Trading Rows opened on 2 December 1893."},
        ],
    },
    "matching": {
        "title": "Match the Eras",
        "intro": "Choose the year associated with each landmark. The server checks your answers and provides the explanations.",
        "pairs": [
            {"id": "cathedral-year", "left": "Cathedral of the Annunciation", "explanation": "The Cathedral of the Annunciation in the Moscow Kremlin was consecrated in 1489."},
            {"id": "gum-year", "left": "Upper Trading Rows", "explanation": "The Upper Trading Rows, now GUM, opened in 1893."},
            {"id": "vdnh-year", "left": "First VDNKh exhibition", "explanation": "The first All-Union Agricultural Exhibition at VDNKh opened in 1939."},
        ],
        "choices": [
            {"id": "year-1489", "label": "1489"},
            {"id": "year-1893", "label": "1893"},
            {"id": "year-1939", "label": "1939"},
        ],
    },
    "timeline": {
        "title": "Build the Timeline",
        "intro": "Arrange events from earliest to latest using the up and down buttons, then check the order.",
        "items": [
            {"id": "metro-1935", "label": "The first section of the Moscow Metro opened", "explanation": "The first section of the Moscow Metro opened on 15 May 1935."},
            {"id": "gum-1893", "label": "The Upper Trading Rows opened", "explanation": "The Upper Trading Rows, now GUM, opened on 2 December 1893."},
            {"id": "vdnh-1939", "label": "The first exhibition at VDNKh opened", "explanation": "The first All-Union Agricultural Exhibition at VDNKh opened in 1939."},
        ],
    },
    "word_blocks": {
        "title": "Build the Phrase",
        "intro": "Arrange the words into a natural sentence using the up and down buttons, then check it.",
        "blocks": [
            {"id": "word-capital", "label": "capital"},
            {"id": "word-russia", "label": "of Russia"},
            {"id": "word-moscow", "label": "Moscow"},
            {"id": "word-dash", "label": "—"},
        ],
        "explanation": "Correct: ‘Moscow is the capital of Russia.’",
    },
    "price_slider": {
        "title": "Guess the Fare",
        "intro": "Move the slider to estimate the historical fare. The server checks the allowed range and exact answer.",
        "question": "How much was a ticket for the first Moscow Metro line on opening day?",
        "fact_date": "15 May 1935",
        "unit": "kopeks",
        "explanation": "On 15 May 1935, the opening day of the first Moscow Metro line, a ride cost 50 kopeks.",
    },
    "photo_scanner": {
        "title": "Photo Scanner: Kremlin Wall",
        "intro": "Look at the original Red Square photo and select the area with the Kremlin wall's merlons.",
        "question": "Where can you see the Kremlin wall's merlons in the photo?",
        "image_alt": "A photograph of the Kremlin wall on Moscow's Red Square beneath a blue sky",
        "field_note": "This is an on-screen exercise using a licensed photo; camera, geolocation, and AR are not connected.",
        "explanation": "The merlons run along the top of the Kremlin wall. Compare the detail with the image caption and license.",
    },
}


def upgrade() -> None:
    op.execute(
        sa.text("""
            UPDATE game_content_translation
            SET payload = payload || CAST(:overlay AS jsonb), updated_at = now()
            WHERE id = :translation_id
              AND content_revision_id = :content_revision_id
              AND language = 'en'
        """).bindparams(
            overlay=json.dumps(activity_payload, ensure_ascii=False),
            translation_id=TRANSLATION_ID,
            content_revision_id=CONTENT_REVISION_ID,
        )
    )


def downgrade() -> None:
    op.execute(sa.text("""
        UPDATE game_content_translation
        SET payload = payload - ARRAY[
            'truth_myth', 'matching', 'timeline', 'word_blocks', 'price_slider', 'photo_scanner'
        ]::text[], updated_at = now()
        WHERE id = 'moscow-sandbox-v8-en-v1'
          AND content_revision_id = 'moscow-sandbox-activities-v8'
          AND language = 'en'
    """))
