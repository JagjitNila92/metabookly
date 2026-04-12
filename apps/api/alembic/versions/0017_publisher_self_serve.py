"""Publisher self-serve: plan tier on feed_sources + api key table

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add plan tier to feed_sources (free | starter | pro)
    op.add_column(
        "feed_sources",
        sa.Column("plan", sa.Text, nullable=False, server_default="free"),
    )

    # 2. Store contact_name on feed_sources for self-registered publishers
    op.add_column(
        "feed_sources",
        sa.Column("contact_name", sa.Text, nullable=True),
    )

    # 3. API keys table — supports multiple named keys per feed source
    op.create_table(
        "feed_source_api_keys",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "feed_source_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("feed_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key_hash", sa.Text, nullable=False),
        sa.Column("key_prefix", sa.Text, nullable=False),   # e.g. "mb_live_a1b2" — shown in UI
        sa.Column("label", sa.Text, nullable=True),         # optional human name
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("feed_source_api_keys_feed_source_idx", "feed_source_api_keys", ["feed_source_id"])
    op.create_index("feed_source_api_keys_prefix_idx", "feed_source_api_keys", ["key_prefix"], unique=True)


def downgrade() -> None:
    op.drop_table("feed_source_api_keys")
    op.drop_column("feed_sources", "contact_name")
    op.drop_column("feed_sources", "plan")
