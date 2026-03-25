"""Publisher portal: FeedSource, OnixFeedV2, BookEditorialLayer, MetadataConflict, AiSuggestion, BookMetadataVersion

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # feed_sources — publishers/distributors/aggregators that send us ONIX
    op.create_table(
        "feed_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),   # publisher | distributor | aggregator
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="20"),
        sa.Column("cognito_sub", sa.Text(), unique=True),
        sa.Column("api_key_hash", sa.Text()),
        sa.Column("api_key_prefix", sa.Text()),
        sa.Column("contact_email", sa.Text()),
        sa.Column("webhook_url", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("feed_sources_cognito_sub_idx", "feed_sources", ["cognito_sub"])
    op.create_index("feed_sources_source_type_idx", "feed_sources", ["source_type"])

    # onix_feeds_v2 — extended feed tracking for portal submissions
    op.create_table(
        "onix_feeds_v2",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("feed_source_id", UUID(as_uuid=True), sa.ForeignKey("feed_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("s3_bucket", sa.Text(), nullable=False),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text()),
        sa.Column("file_size_bytes", sa.Integer()),
        sa.Column("onix_version", sa.Text()),              # "2.1" or "3.0"
        sa.Column("sequence_number", sa.Integer()),        # from publisher's sequence
        sa.Column("expected_sequence", sa.Integer()),      # what we expected
        sa.Column("gaps_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("records_found", sa.Integer()),
        sa.Column("records_upserted", sa.Integer()),
        sa.Column("records_failed", sa.Integer()),
        sa.Column("records_skipped", sa.Integer()),
        sa.Column("records_conflicted", sa.Integer()),
        sa.Column("error_detail", sa.Text()),
        sa.Column("sample_errors", JSONB),
        sa.Column("triggered_by", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("onix_feeds_v2_feed_source_idx", "onix_feeds_v2", ["feed_source_id"])
    op.create_index("onix_feeds_v2_status_idx", "onix_feeds_v2", ["status"])
    op.create_index("onix_feeds_v2_created_idx", "onix_feeds_v2", ["created_at"])

    # book_editorial_layers — editorial overrides that survive ONIX re-ingestion
    op.create_table(
        "book_editorial_layers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("toc", sa.Text()),
        sa.Column("excerpt", sa.Text()),
        sa.Column("extra_subjects", JSONB),
        sa.Column("field_sources", JSONB),
        sa.Column("edited_by", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("book_editorial_layers_book_id_idx", "book_editorial_layers", ["book_id"])

    # metadata_conflicts — queued conflicts when feed updates touch editorially-modified fields
    op.create_table(
        "metadata_conflicts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feed_id", UUID(as_uuid=True), sa.ForeignKey("onix_feeds_v2.id", ondelete="SET NULL")),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("onix_value", sa.Text()),
        sa.Column("editorial_value", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("resolved_by", sa.Text()),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("metadata_conflicts_book_id_idx", "metadata_conflicts", ["book_id"])
    op.create_index("metadata_conflicts_status_idx", "metadata_conflicts", ["status"])

    # ai_suggestions — AI-generated metadata improvements awaiting review
    op.create_table(
        "ai_suggestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("original_value", sa.Text()),
        sa.Column("suggested_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Text(), nullable=False),   # high | medium | low
        sa.Column("model_id", sa.Text()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("reviewed_by", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ai_suggestions_book_id_idx", "ai_suggestions", ["book_id"])
    op.create_index("ai_suggestions_status_confidence_idx", "ai_suggestions", ["status", "confidence"])

    # book_metadata_versions — point-in-time snapshots for audit trail and rollback
    op.create_table(
        "book_metadata_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("changed_by", sa.Text(), nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("book_metadata_versions_book_id_idx", "book_metadata_versions", ["book_id"])
    op.create_index(
        "book_metadata_versions_book_version_idx",
        "book_metadata_versions", ["book_id", "version_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("book_metadata_versions")
    op.drop_table("ai_suggestions")
    op.drop_table("metadata_conflicts")
    op.drop_table("book_editorial_layers")
    op.drop_table("onix_feeds_v2")
    op.drop_table("feed_sources")
