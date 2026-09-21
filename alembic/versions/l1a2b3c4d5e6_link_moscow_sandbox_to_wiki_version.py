"""link Moscow sandbox facts to a published Wiki version

Revision ID: l1a2b3c4d5e6
Revises: k0f1a2b3c4d5
Create Date: 2026-09-21
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "k0f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.execute(sa.text("""
        INSERT INTO game_content_revision (id, kind, payload, is_published, published_at, created_at, updated_at)
        SELECT 'moscow-sandbox-activities-v8', 'sandbox-activities',
          payload || CAST('{"id":"moscow-sandbox-activities-v8","wiki_reference":{"slug":"moscow","version_id":"wiki-moscow-v1"}}' AS jsonb),
          TRUE, :now, :now, :now
        FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v7'
    """).bindparams(now=now))
    op.execute(sa.text("UPDATE game_city SET sandbox_content_revision_id = 'moscow-sandbox-activities-v8' WHERE id = 'moscow'"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM game_attempt WHERE content_revision_id = 'moscow-sandbox-activities-v8'"))
    op.execute(sa.text("UPDATE game_city SET sandbox_content_revision_id = 'moscow-sandbox-activities-v7' WHERE id = 'moscow'"))
    op.execute(sa.text("DELETE FROM game_content_revision WHERE id = 'moscow-sandbox-activities-v8'"))
