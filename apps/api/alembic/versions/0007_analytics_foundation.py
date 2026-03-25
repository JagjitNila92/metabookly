"""Analytics foundation — book_distributors junction, feed source distributor ownership,
and event tracking tables (search, view, price check).

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── feed_sources: which distributor owns this feed ────────────────────────
    op.add_column("feed_sources", sa.Column("distributor_code", sa.Text(), nullable=True))
    op.add_column("feed_sources", sa.Column("managed_by", sa.Text(),
                  server_default="distributor", nullable=False))
    op.create_index("feed_sources_distributor_code_idx", "feed_sources", ["distributor_code"])

    # ── book_distributors: which distributor carries which title ───────────────
    op.create_table(
        "book_distributors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True),
                  sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("distributor_code", sa.Text(), nullable=False),
        sa.Column("feed_source_id", UUID(as_uuid=True),
                  sa.ForeignKey("feed_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("book_id", "distributor_code", name="uq_book_distributor"),
    )
    op.create_index("book_distributors_book_id_idx", "book_distributors", ["book_id"])
    op.create_index("book_distributors_distributor_code_idx", "book_distributors", ["distributor_code"])

    # ── search_events ─────────────────────────────────────────────────────────
    op.create_table(
        "search_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("filters", JSONB(), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("search_events_retailer_id_idx", "search_events", ["retailer_id"])
    op.create_index("search_events_created_at_idx", "search_events", ["created_at"])

    # ── book_view_events ──────────────────────────────────────────────────────
    op.create_table(
        "book_view_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("book_id", UUID(as_uuid=True),
                  sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("isbn13", sa.Text(), nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("book_view_events_book_id_idx", "book_view_events", ["book_id"])
    op.create_index("book_view_events_retailer_id_idx", "book_view_events", ["retailer_id"])
    op.create_index("book_view_events_created_at_idx", "book_view_events", ["created_at"])

    # ── price_check_events ────────────────────────────────────────────────────
    op.create_table(
        "price_check_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("book_id", UUID(as_uuid=True),
                  sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("isbn13", sa.Text(), nullable=False),
        # Which distributors were queried and which actually returned a price
        sa.Column("distributors_queried", JSONB(), nullable=False),
        sa.Column("distributors_with_price", JSONB(), nullable=False),
        # True if queried at least one distributor but got no price back
        sa.Column("had_gap", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("price_check_events_book_id_idx", "price_check_events", ["book_id"])
    op.create_index("price_check_events_retailer_id_idx", "price_check_events", ["retailer_id"])
    op.create_index("price_check_events_created_at_idx", "price_check_events", ["created_at"])
    op.create_index("price_check_events_had_gap_idx", "price_check_events", ["had_gap"])


def downgrade() -> None:
    op.drop_table("price_check_events")
    op.drop_table("book_view_events")
    op.drop_table("search_events")
    op.drop_table("book_distributors")
    op.drop_index("feed_sources_distributor_code_idx", "feed_sources")
    op.drop_column("feed_sources", "managed_by")
    op.drop_column("feed_sources", "distributor_code")
