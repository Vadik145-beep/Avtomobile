"""Initial schema: users, leads, transactions, lead_deliveries, distribution_settings

Revision ID: 0001
Revises:
Create Date: 2026-03-18 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enum types ---
    distributionmode = postgresql.ENUM(
        "exclusive", "speed", "coverage", name="distributionmode"
    )
    transactiontype = postgresql.ENUM(
        "purchase", "debit", "bonus", name="transactiontype"
    )
    deliverystatus = postgresql.ENUM(
        "sent", "opened", "blocked", name="deliverystatus"
    )

    distributionmode.create(op.get_bind(), checkfirst=True)
    transactiontype.create(op.get_bind(), checkfirst=True)
    deliverystatus.create(op.get_bind(), checkfirst=True)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("limit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    # --- leads ---
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("phone_encrypted", sa.Text(), nullable=True),
        sa.Column("recording_url", sa.Text(), nullable=True),
        sa.Column(
            "distribution_mode",
            postgresql.ENUM(
                "exclusive",
                "speed",
                "coverage",
                name="distributionmode",
                create_type=False,
            ),
            nullable=False,
            server_default="coverage",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- transactions ---
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "purchase",
                "debit",
                "bonus",
                name="transactiontype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])

    # --- lead_deliveries ---
    op.create_table(
        "lead_deliveries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "sent",
                "opened",
                "blocked",
                name="deliverystatus",
                create_type=False,
            ),
            nullable=False,
            server_default="sent",
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_deliveries_lead_id", "lead_deliveries", ["lead_id"])
    op.create_index("ix_lead_deliveries_user_id", "lead_deliveries", ["user_id"])

    # --- distribution_settings ---
    op.create_table(
        "distribution_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "mode",
            postgresql.ENUM(
                "exclusive",
                "speed",
                "coverage",
                name="distributionmode",
                create_type=False,
            ),
            nullable=False,
            server_default="coverage",
        ),
        sa.Column("speed_group_size", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed default distribution settings row
    op.execute(
        "INSERT INTO distribution_settings (mode, speed_group_size) VALUES ('coverage', 5)"
    )


def downgrade() -> None:
    op.drop_table("distribution_settings")
    op.drop_index("ix_lead_deliveries_user_id", table_name="lead_deliveries")
    op.drop_index("ix_lead_deliveries_lead_id", table_name="lead_deliveries")
    op.drop_table("lead_deliveries")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("leads")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

    sa.Enum(name="deliverystatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="transactiontype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="distributionmode").drop(op.get_bind(), checkfirst=True)
