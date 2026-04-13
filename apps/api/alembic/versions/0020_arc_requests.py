"""add ARC requests — arc_enabled/arc_s3_key on books, arc_requests table

Revision ID: 0020
Revises: 0019
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ARC columns to books
    op.add_column("books", sa.Column("arc_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("books", sa.Column("arc_s3_key", sa.Text(), nullable=True))

    # ARC requests table
    op.create_table(
        "arc_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feed_source_id", UUID(as_uuid=True), sa.ForeignKey("feed_sources.id", ondelete="SET NULL"), nullable=True),
        # Who requested it
        sa.Column("requester_retailer_id", UUID(as_uuid=True), sa.ForeignKey("retailers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requester_name", sa.Text(), nullable=False),
        sa.Column("requester_email", sa.Text(), nullable=False),
        sa.Column("requester_company", sa.Text(), nullable=True),
        sa.Column("requester_type", sa.Text(), nullable=False),   # retailer | trade_press | blogger | other
        sa.Column("requester_message", sa.Text(), nullable=True),
        # Decision
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),  # pending | approved | declined
        sa.Column("decline_reason", sa.Text(), nullable=True),
        sa.Column("approved_expires_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.Text(), nullable=True),       # Cognito sub of publisher user
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("arc_requests_book_id_idx", "arc_requests", ["book_id"])
    op.create_index("arc_requests_feed_source_id_idx", "arc_requests", ["feed_source_id"])
    op.create_index("arc_requests_status_idx", "arc_requests", ["status"])
    op.create_index("arc_requests_requester_email_idx", "arc_requests", ["requester_email"])


def downgrade() -> None:
    op.drop_table("arc_requests")
    op.drop_column("books", "arc_s3_key")
    op.drop_column("books", "arc_enabled")
