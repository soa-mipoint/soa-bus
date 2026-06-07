"""add booking snapshot fields

Revision ID: 003
Revises: 002
Create Date: 2026-06-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("cliente_nombre_snapshot", sa.String(length=255), nullable=True))
    op.add_column("bookings", sa.Column("space_nombre_snapshot", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "space_nombre_snapshot")
    op.drop_column("bookings", "cliente_nombre_snapshot")
