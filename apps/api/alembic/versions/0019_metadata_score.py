"""Add metadata_score to books

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column("metadata_score", sa.SmallInteger, nullable=True),
    )
    op.create_index("books_metadata_score_idx", "books", ["metadata_score"])


def downgrade() -> None:
    op.drop_index("books_metadata_score_idx")
    op.drop_column("books", "metadata_score")
