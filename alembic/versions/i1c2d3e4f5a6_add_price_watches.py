"""Add per-user deduplicated price watches."""
from alembic import op
import sqlalchemy as sa
revision = "i1c2d3e4f5a6"
down_revision = "h0b1c2d3e4f5"
branch_labels = depends_on = None
def upgrade():
    op.create_table("price_watch", sa.Column("id", sa.String(32), primary_key=True), sa.Column("user_id", sa.String(), nullable=False), sa.Column("subject_key", sa.String(200), nullable=False), sa.Column("threshold_minor", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("last_alerted_amount_minor", sa.Integer(), nullable=True), sa.Column("last_alerted_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("threshold_minor >= 0", name="price_watch_nonnegative_threshold"), sa.CheckConstraint("char_length(currency) = 3", name="price_watch_currency"), sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"), sa.UniqueConstraint("user_id", "subject_key", "currency", name="uq_price_watch_user_subject_currency"))
    op.create_index("idx_price_watch_active_subject", "price_watch", ["active", "subject_key"])
def downgrade():
    op.drop_index("idx_price_watch_active_subject", table_name="price_watch")
    op.drop_table("price_watch")
