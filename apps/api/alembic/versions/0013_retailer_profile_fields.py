"""Add contact_name, phone, role, referral_source to retailers table.

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("retailers", sa.Column("contact_name", sa.Text(), nullable=True))
    op.add_column("retailers", sa.Column("phone", sa.Text(), nullable=True))
    op.add_column("retailers", sa.Column("role", sa.Text(), nullable=True))
    op.add_column("retailers", sa.Column("referral_source", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("retailers", "referral_source")
    op.drop_column("retailers", "role")
    op.drop_column("retailers", "phone")
    op.drop_column("retailers", "contact_name")
