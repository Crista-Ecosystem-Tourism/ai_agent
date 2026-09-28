"""Merge the current ai_agent migration heads.

Revision ID: f1a2b3c4d5e6
Revises: d2e3f4a5b6c7, d60b1c2d3e4, f0e1d2c3b4a5, j2d3e4f5a6b7
"""
from typing import Sequence, Union


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = (
    "d2e3f4a5b6c7",
    "d60b1c2d3e4",
    "f0e1d2c3b4a5",
    "j2d3e4f5a6b7",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
