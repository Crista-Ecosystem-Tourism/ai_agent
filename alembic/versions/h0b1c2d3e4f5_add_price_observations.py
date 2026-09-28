"""Add sourced price observations with explicit freshness."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "h0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "g9a0b1c2d3e4"
branch_labels = depends_on = None
def upgrade() -> None:
    op.create_table("price_observation", sa.Column("id", sa.String(32), primary_key=True), sa.Column("subject_key", sa.String(200), nullable=False), sa.Column("source", sa.String(48), nullable=False), sa.Column("source_url", sa.String(2048), nullable=False), sa.Column("amount_minor", sa.Integer, nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("amount_minor >= 0", name="price_observation_nonnegative"), sa.CheckConstraint("char_length(currency) = 3", name="price_observation_currency"), sa.CheckConstraint("expires_at > observed_at", name="price_observation_positive_ttl"))
    op.create_index("idx_price_observation_subject_freshness", "price_observation", ["subject_key", "expires_at", "observed_at"])
def downgrade() -> None:
    op.drop_index("idx_price_observation_subject_freshness", table_name="price_observation")
    op.drop_table("price_observation")
