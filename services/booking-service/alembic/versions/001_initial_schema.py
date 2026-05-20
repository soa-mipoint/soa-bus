"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE booking_status AS ENUM ('PENDIENTE', 'CONFIRMADA', 'CANCELADA', 'PAGADA');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo_reserva", sa.String(20), nullable=False, unique=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anfitrion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("num_personas", sa.Integer, nullable=False),
        sa.Column("estado", sa.Enum("PENDIENTE", "CONFIRMADA", "CANCELADA", "PAGADA", name="booking_status"), nullable=False, server_default="PENDIENTE"),
        sa.Column("motivo_cancelacion", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bookings_id", "bookings", ["id"])
    op.create_index("ix_bookings_codigo_reserva", "bookings", ["codigo_reserva"])
    op.create_index("ix_bookings_cliente_id", "bookings", ["cliente_id"])
    op.create_index("ix_bookings_space_id", "bookings", ["space_id"])
    op.create_index("ix_bookings_estado", "bookings", ["estado"])

    op.create_table(
        "booking_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("estado_anterior", sa.String(20), nullable=True),
        sa.Column("estado_nuevo", sa.String(20), nullable=False),
        sa.Column("nota", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_booking_status_history_booking_id", "booking_status_history", ["booking_id"])


def downgrade() -> None:
    op.drop_table("booking_status_history")
    op.drop_table("bookings")
    op.execute("DROP TYPE booking_status")
