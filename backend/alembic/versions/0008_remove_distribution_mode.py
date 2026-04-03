"""Remove DistributionMode: drop distribution_mode from leads, mode and speed_group_size from distribution_settings, drop distributionmode enum

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("leads", "distribution_mode")
    op.drop_column("distribution_settings", "mode")
    op.drop_column("distribution_settings", "speed_group_size")
    op.execute("DROP TYPE IF EXISTS distributionmode")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE distributionmode AS ENUM ('exclusive', 'speed', 'coverage')"
    )
    op.add_column(
        "distribution_settings",
        sa.Column(
            "speed_group_size",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
    )
    op.add_column(
        "distribution_settings",
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
    )
    op.add_column(
        "leads",
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
    )
