"""Create feature flags tables.

global_feature_flags  — platform-wide switches (e.g. ordering_enabled)
account_feature_flags — per-account overrides that shadow global flags

Seed: ordering_enabled = false (ordering hidden until ~50 publishers onboard)

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Global flags ──────────────────────────────────────────────────────────
    op.create_table(
        "global_feature_flags",
        sa.Column("flag_name", sa.Text(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Who last changed it (Cognito sub of admin)
        sa.Column("updated_by", sa.Text(), nullable=True),
    )

    # ── Per-account overrides ─────────────────────────────────────────────────
    # account_type: retailer | publisher | distributor
    # When present, this shadows the global flag for that specific account.
    op.create_table(
        "account_feature_flags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("account_type", sa.Text(), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flag_name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_by", sa.Text(), nullable=True),
    )

    op.create_unique_constraint(
        "uq_account_feature_flags",
        "account_feature_flags",
        ["account_type", "account_id", "flag_name"],
    )
    op.create_index(
        "ix_account_feature_flags_account",
        "account_feature_flags",
        ["account_type", "account_id"],
    )
    op.create_index(
        "ix_account_feature_flags_flag_name",
        "account_feature_flags",
        ["flag_name"],
    )

    # ── Seed global flags ─────────────────────────────────────────────────────
    op.execute("""
        INSERT INTO global_feature_flags (flag_name, enabled, description)
        VALUES
            ('ordering_enabled',   false, 'Show basket, checkout, and ordering UI to all retailers. Flip when ~50 publishers are onboard.'),
            ('publisher_analytics', true, 'Publisher analytics dashboard — views, orders, top titles, genre breakdown.'),
            ('ai_suggestions',      false, 'AI metadata suggestions in the publisher portal (Bedrock, post-MVP).')
    """)


def downgrade() -> None:
    op.drop_index("ix_account_feature_flags_flag_name", "account_feature_flags")
    op.drop_index("ix_account_feature_flags_account", "account_feature_flags")
    op.drop_constraint("uq_account_feature_flags", "account_feature_flags")
    op.drop_table("account_feature_flags")
    op.drop_table("global_feature_flags")
