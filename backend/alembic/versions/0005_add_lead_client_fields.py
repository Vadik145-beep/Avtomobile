"""Add client_name, country_origin, timing to leads

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("client_name", sa.String(255), nullable=True))
    op.add_column("leads", sa.Column("country_origin", sa.String(255), nullable=True))
    op.add_column("leads", sa.Column("timing", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "timing")
    op.drop_column("leads", "country_origin")
    op.drop_column("leads", "client_name")
