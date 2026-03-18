"""Add call_id, transcript, is_qualified to leads

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("call_id", sa.String(36), nullable=True))
    op.add_column("leads", sa.Column("transcript", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("is_qualified", sa.Boolean(), nullable=True))
    op.create_index("ix_leads_call_id", "leads", ["call_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_leads_call_id", table_name="leads")
    op.drop_column("leads", "is_qualified")
    op.drop_column("leads", "transcript")
    op.drop_column("leads", "call_id")
