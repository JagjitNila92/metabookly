"""add publisher_assets table — per-title marketing files (PDFs, press kits, author photos)

Revision ID: 0021
Revises: 0020
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publisher_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feed_source_id", UUID(as_uuid=True), sa.ForeignKey("feed_sources.id", ondelete="SET NULL"), nullable=True),
        # File info
        sa.Column("asset_type", sa.Text(), nullable=False),   # press_kit | author_photo | sell_sheet | media_pack | other
        sa.Column("label", sa.Text(), nullable=False),        # human-readable name, e.g. "Press Kit Q1 2026"
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=True),  # MIME type
        # Visibility
        sa.Column("public", sa.Boolean(), nullable=False, server_default="true"),  # visible to retailers
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("publisher_assets_book_id_idx", "publisher_assets", ["book_id"])
    op.create_index("publisher_assets_feed_source_id_idx", "publisher_assets", ["feed_source_id"])
    op.create_index("publisher_assets_asset_type_idx", "publisher_assets", ["asset_type"])


def downgrade() -> None:
    op.drop_table("publisher_assets")
