"""Widen call_id from VARCHAR(36) to VARCHAR(128)

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "leads",
        "call_id",
        existing_type=sa.String(36),
        type_=sa.String(128),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "leads",
        "call_id",
        existing_type=sa.String(128),
        type_=sa.String(36),
        existing_nullable=True,
    )
