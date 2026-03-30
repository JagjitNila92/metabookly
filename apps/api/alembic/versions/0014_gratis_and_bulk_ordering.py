"""Add gratis_enabled to retailer_distributors, order_type to orders,
and isbn_lists + isbn_list_items for saved order lists.

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Gratis permission: per-retailer, per-distributor flag set by admin on approval
    op.add_column(
        "retailer_distributors",
        sa.Column("gratis_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Order type: trade (default) | gratis | sample
    op.add_column(
        "orders",
        sa.Column("order_type", sa.Text(), nullable=False, server_default="trade"),
    )

    # Saved ISBN lists — retailer can name and persist a list of ISBNs for later
    op.create_table(
        "isbn_lists",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "isbn_list_items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("list_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("isbn_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("isbn13", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_unique_constraint(
        "uq_isbn_list_items_list_isbn", "isbn_list_items", ["list_id", "isbn13"]
    )
    op.create_index("ix_isbn_lists_retailer_id", "isbn_lists", ["retailer_id"])
    op.create_index("ix_isbn_list_items_list_id", "isbn_list_items", ["list_id"])


def downgrade() -> None:
    op.drop_index("ix_isbn_list_items_list_id", "isbn_list_items")
    op.drop_index("ix_isbn_lists_retailer_id", "isbn_lists")
    op.drop_constraint("uq_isbn_list_items_list_isbn", "isbn_list_items")
    op.drop_table("isbn_list_items")
    op.drop_table("isbn_lists")
    op.drop_column("orders", "order_type")
    op.drop_column("retailer_distributors", "gratis_enabled")
