"""add game geography and path nodes

Revision ID: b4e8a1d2c3f6
Revises: a9c7d4e1f2b3
Create Date: 2026-09-16
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e8a1d2c3f6"
down_revision: Union[str, Sequence[str], None] = "a9c7d4e1f2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_country",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "game_region",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("country_id", sa.String(), sa.ForeignKey("game_country.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("country_id", "position", name="uq_game_region_country_position"),
    )
    op.create_table(
        "game_city",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("region_id", sa.String(), sa.ForeignKey("game_region.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_game_city_region", "game_city", ["region_id"])
    op.create_table(
        "game_quest",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("city_id", sa.String(), sa.ForeignKey("game_city.id"), nullable=False),
        sa.Column("content_revision_id", sa.String(), sa.ForeignKey("game_content_revision.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("city_id", "position", name="uq_game_quest_city_position"),
    )
    op.create_index("idx_game_quest_city_published", "game_quest", ["city_id", "is_published"])
    op.create_table(
        "game_quest_completion",
        sa.Column("user_id", sa.String(), sa.ForeignKey("app_user.id"), primary_key=True),
        sa.Column("quest_id", sa.String(), sa.ForeignKey("game_quest.id"), primary_key=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )

    now = datetime.now(timezone.utc)
    country = sa.table("game_country", sa.column("id", sa.String()), sa.column("name", sa.String()), sa.column("is_published", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    region = sa.table("game_region", sa.column("id", sa.String()), sa.column("country_id", sa.String()), sa.column("name", sa.String()), sa.column("position", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    city = sa.table("game_city", sa.column("id", sa.String()), sa.column("region_id", sa.String()), sa.column("name", sa.String()), sa.column("tier", sa.Integer()), sa.column("is_published", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    quest = sa.table("game_quest", sa.column("id", sa.String()), sa.column("city_id", sa.String()), sa.column("content_revision_id", sa.String()), sa.column("kind", sa.String()), sa.column("position", sa.Integer()), sa.column("is_published", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    op.bulk_insert(country, [{"id": "ru", "name": "Россия", "is_published": True, "created_at": now, "updated_at": now}])
    op.bulk_insert(region, [{"id": "ru-moscow", "country_id": "ru", "name": "Москва", "position": 1, "created_at": now, "updated_at": now}])
    op.bulk_insert(city, [{"id": "moscow", "region_id": "ru-moscow", "name": "Москва", "tier": 1, "is_published": True, "created_at": now, "updated_at": now}])
    op.bulk_insert(quest, [{"id": "moscow-red-square", "city_id": "moscow", "content_revision_id": "onboarding-moscow-v1", "kind": "onboarding", "position": 1, "is_published": True, "created_at": now, "updated_at": now}])


def downgrade() -> None:
    op.drop_table("game_quest_completion")
    op.drop_index("idx_game_quest_city_published", table_name="game_quest")
    op.drop_table("game_quest")
    op.drop_index("idx_game_city_region", table_name="game_city")
    op.drop_table("game_city")
    op.drop_table("game_region")
    op.drop_table("game_country")
