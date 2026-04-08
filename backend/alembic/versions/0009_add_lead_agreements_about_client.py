"""Add agreements and about_client to leads

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("agreements", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("about_client", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "about_client")
    op.drop_column("leads", "agreements")
