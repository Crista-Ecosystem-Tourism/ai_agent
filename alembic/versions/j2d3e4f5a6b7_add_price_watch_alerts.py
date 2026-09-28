"""Persist user-visible deduplicated price watch alerts."""
from alembic import op
import sqlalchemy as sa
revision = "j2d3e4f5a6b7"
down_revision = "i1c2d3e4f5a6"
branch_labels = depends_on = None
def upgrade():
    op.create_table("price_watch_alert", sa.Column("id", sa.String(32), primary_key=True), sa.Column("watch_id", sa.String(32), nullable=False), sa.Column("user_id", sa.String(), nullable=False), sa.Column("subject_key", sa.String(200), nullable=False), sa.Column("amount_minor", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["watch_id"], ["price_watch.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"))
    op.create_index("idx_price_watch_alert_user_created", "price_watch_alert", ["user_id", "created_at"])
def downgrade():
    op.drop_index("idx_price_watch_alert_user_created", table_name="price_watch_alert")
    op.drop_table("price_watch_alert")
