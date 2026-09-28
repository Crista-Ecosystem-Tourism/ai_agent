"""Give the generic city-quest API the onboarding stamp metadata.

Revision ID: g1a2b3c4d5e6
Revises: f1a2b3c4d5e6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("""
        UPDATE game_content_revision
        SET payload = jsonb_set(
            payload,
            '{reward,stamp_key}',
            to_jsonb(CAST(:stamp_key AS text)),
            true
        )
        WHERE id = :content_id
    """).bindparams(
        stamp_key="moscow-starter",
        content_id="onboarding-moscow-v1",
    ))


def downgrade() -> None:
    op.execute(sa.text("""
        UPDATE game_content_revision
        SET payload = jsonb_set(
            payload,
            '{reward}',
            (payload -> 'reward') - 'stamp_key',
            true
        )
        WHERE id = :content_id
    """).bindparams(content_id="onboarding-moscow-v1"))
