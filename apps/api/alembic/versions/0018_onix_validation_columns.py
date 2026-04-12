"""Add validation columns to onix_feeds_v2

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("onix_feeds_v2", sa.Column("validation_passed", sa.Boolean, nullable=True))
    op.add_column("onix_feeds_v2", sa.Column("validation_errors_count", sa.Integer, nullable=True))
    op.add_column("onix_feeds_v2", sa.Column("validation_warnings_count", sa.Integer, nullable=True))
    op.add_column("onix_feeds_v2", sa.Column("validation_errors", sa.dialects.postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("onix_feeds_v2", "validation_errors")
    op.drop_column("onix_feeds_v2", "validation_warnings_count")
    op.drop_column("onix_feeds_v2", "validation_errors_count")
    op.drop_column("onix_feeds_v2", "validation_passed")
