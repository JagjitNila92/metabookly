"""Add height_mm and width_mm to books

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("books", sa.Column("height_mm", sa.SmallInteger(), nullable=True))
    op.add_column("books", sa.Column("width_mm", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("books", "width_mm")
    op.drop_column("books", "height_mm")
