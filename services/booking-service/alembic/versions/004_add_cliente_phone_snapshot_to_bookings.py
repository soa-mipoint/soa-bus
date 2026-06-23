"""add cliente phone snapshot to bookings

Revision ID: 004
Revises: 003
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("cliente_phone_snapshot", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "cliente_phone_snapshot")
