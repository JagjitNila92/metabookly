"""Basket and basket items for retailer ordering.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # baskets — one per retailer, server-side persistent basket
    op.create_table(
        "baskets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("baskets_retailer_id_idx", "baskets", ["retailer_id"])

    # basket_items — one row per ISBN in the basket
    op.create_table(
        "basket_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("basket_id", UUID(as_uuid=True),
                  sa.ForeignKey("baskets.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("book_id", UUID(as_uuid=True),
                  sa.ForeignKey("books.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("isbn13", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),          # min 1
        sa.Column("preferred_distributor_code", sa.Text()),           # NULL = auto-route
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("basket_items_basket_id_idx", "basket_items", ["basket_id"])
    op.create_unique_constraint("uq_basket_items_basket_isbn", "basket_items",
                                ["basket_id", "isbn13"])


def downgrade() -> None:
    op.drop_table("basket_items")
    op.drop_table("baskets")
