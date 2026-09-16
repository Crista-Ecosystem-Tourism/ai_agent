"""legacy suitcase ownership boundary

Revision ID: f7a1b2c3d4e5
Revises: e4f8a2b5c7d9
Create Date: 2026-04-28

"""
from typing import Sequence, Union

revision: str = 'f7a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e4f8a2b5c7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Keep the historical revision without claiming Suitcase tables on new DBs.

    Deployments that previously ran this revision already retain their data.
    `suitcase/backend` is the sole schema owner for these tables going forward.
    """


def downgrade() -> None:
    # These tables belong to suitcase/backend and must not be removed by an
    # ai_agent downgrade.
    pass
