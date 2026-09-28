"""add editorial star route pipeline

Revision ID: a0b1c2d3e4f5
Revises: z9a0b1c2d3e4
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a0b1c2d3e4f5"
down_revision = "z9a0b1c2d3e4"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "star_route_transcript",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("author_name", sa.String(), nullable=True),
        sa.Column("rights_basis", sa.String(), nullable=False),
        sa.Column("registered_by", sa.String(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "star_route_segment",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("transcript_id", sa.String(), sa.ForeignKey("star_route_transcript.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_seconds", sa.Integer(), nullable=False),
        sa.Column("end_seconds", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.String(), nullable=False),
        sa.Column("extracted_place_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_star_route_segment_transcript", "star_route_segment", ["transcript_id", "start_seconds"])
    op.create_table(
        "star_route_candidate",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("transcript_id", sa.String(), sa.ForeignKey("star_route_transcript.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("pois", postgresql.JSONB(), nullable=False),
        sa.Column("route_geojson", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reviewed_by", sa.String(), sa.ForeignKey("app_user.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_star_route_candidate_status_published", "star_route_candidate", ["status", "published_at"])
    op.create_index("idx_star_route_candidate_transcript", "star_route_candidate", ["transcript_id"])


def downgrade() -> None:
    op.drop_index("idx_star_route_candidate_transcript", table_name="star_route_candidate")
    op.drop_index("idx_star_route_candidate_status_published", table_name="star_route_candidate")
    op.drop_table("star_route_candidate")
    op.drop_index("idx_star_route_segment_transcript", table_name="star_route_segment")
    op.drop_table("star_route_segment")
    op.drop_table("star_route_transcript")
