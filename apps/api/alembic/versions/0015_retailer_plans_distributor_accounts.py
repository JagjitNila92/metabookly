"""Add plan tier to retailers and create distributor_accounts table.

Retailer plans: free | starter_api | intelligence | enterprise
Distributor accounts: portal logins for distributor staff.

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Retailer plan tier ────────────────────────────────────────────────────
    op.add_column(
        "retailers",
        sa.Column("plan", sa.Text(), nullable=False, server_default="free"),
    )
    op.add_column(
        "retailers",
        sa.Column("plan_activated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "retailers",
        sa.Column("plan_expires_at", sa.DateTime(), nullable=True),
    )
    # Extra seats purchased on top of plan default (billed via Stripe quantity)
    op.add_column(
        "retailers",
        sa.Column("extra_seats", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_index("ix_retailers_plan", "retailers", ["plan"])

    # ── Distributor accounts ──────────────────────────────────────────────────
    # Portal login records for distributor staff. Separate from FeedSource
    # (which is about data pipelines). A distributor account gives portal access
    # to the distributor-side dashboard, analytics, and account management.
    op.create_table(
        "distributor_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("cognito_sub", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "distributor_code",
            sa.Text(),
            sa.ForeignKey("distributor_settings.distributor_code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("contact_name", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_distributor_accounts_cognito_sub",
        "distributor_accounts",
        ["cognito_sub"],
        unique=True,
    )
    op.create_index(
        "ix_distributor_accounts_distributor_code",
        "distributor_accounts",
        ["distributor_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_distributor_accounts_distributor_code", "distributor_accounts")
    op.drop_index("ix_distributor_accounts_cognito_sub", "distributor_accounts")
    op.drop_table("distributor_accounts")

    op.drop_index("ix_retailers_plan", "retailers")
    op.drop_column("retailers", "extra_seats")
    op.drop_column("retailers", "plan_expires_at")
    op.drop_column("retailers", "plan_activated_at")
    op.drop_column("retailers", "plan")
