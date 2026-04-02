"""Add icebreaker_active to users and lead_delivery_mode to distribution_settings

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE leaddeliverymode AS ENUM ('pull_broadcast', 'pull_exclusive')")

    op.add_column(
        "users",
        sa.Column(
            "icebreaker_active",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    op.add_column(
        "distribution_settings",
        sa.Column(
            "lead_delivery_mode",
            sa.Enum("pull_broadcast", "pull_exclusive", name="leaddeliverymode", create_type=False),
            nullable=False,
            server_default="pull_broadcast",
        ),
    )


def downgrade() -> None:
    op.drop_column("distribution_settings", "lead_delivery_mode")
    op.drop_column("users", "icebreaker_active")
    op.execute("DROP TYPE leaddeliverymode")
