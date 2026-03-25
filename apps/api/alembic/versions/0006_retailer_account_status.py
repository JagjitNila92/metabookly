"""Replace active flag on retailer_distributors with a status workflow column.

Status lifecycle: pending → approved | rejected; retailer can withdraw.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "retailer_distributors",
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
    )
    op.add_column(
        "retailer_distributors",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "retailer_distributors",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Migrate existing data: active=True → approved, active=False → withdrawn
    op.execute(
        "UPDATE retailer_distributors SET status = CASE WHEN active THEN 'approved' ELSE 'withdrawn' END"
    )
    op.drop_column("retailer_distributors", "active")


def downgrade() -> None:
    op.add_column(
        "retailer_distributors",
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.execute(
        "UPDATE retailer_distributors SET active = CASE WHEN status = 'approved' THEN true ELSE false END"
    )
    op.drop_column("retailer_distributors", "updated_at")
    op.drop_column("retailer_distributors", "rejection_reason")
    op.drop_column("retailer_distributors", "status")
