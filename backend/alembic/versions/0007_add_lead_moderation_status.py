"""Add moderation_status to leads

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE moderationstatus AS ENUM ('pending', 'approved', 'rejected')")

    op.add_column(
        "leads",
        sa.Column(
            "moderation_status",
            sa.Enum("pending", "approved", "rejected", name="moderationstatus", create_type=False),
            nullable=False,
            server_default="pending",
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "moderation_status")
    op.execute("DROP TYPE moderationstatus")
