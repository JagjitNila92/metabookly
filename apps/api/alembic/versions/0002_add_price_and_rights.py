"""Add publishing_status, uk_rights, rrp_gbp, rrp_usd to books

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("books", sa.Column("publishing_status", sa.Text, nullable=True))
    op.add_column("books", sa.Column("uk_rights", sa.Boolean, nullable=True))
    op.add_column("books", sa.Column("rrp_gbp", sa.Numeric(10, 2), nullable=True))
    op.add_column("books", sa.Column("rrp_usd", sa.Numeric(10, 2), nullable=True))

    op.create_index("books_uk_rights_idx", "books", ["uk_rights"])
    op.create_index("books_publishing_status_idx", "books", ["publishing_status"])


def downgrade() -> None:
    op.drop_index("books_publishing_status_idx", "books")
    op.drop_index("books_uk_rights_idx", "books")
    op.drop_column("books", "rrp_usd")
    op.drop_column("books", "rrp_gbp")
    op.drop_column("books", "uk_rights")
    op.drop_column("books", "publishing_status")
