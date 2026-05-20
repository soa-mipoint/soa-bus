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
            CREATE TYPE space_status AS ENUM ('ACTIVO', 'INACTIVO', 'PENDIENTE');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("anfitrion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("direccion", sa.String(500), nullable=False),
        sa.Column("distrito", sa.String(100), nullable=False),
        sa.Column("capacidad", sa.Integer, nullable=False),
        sa.Column("precio_hora", sa.Float, nullable=False),
        sa.Column("estado", sa.Enum("ACTIVO", "INACTIVO", "PENDIENTE", name="space_status"), nullable=False, server_default="PENDIENTE"),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_spaces_id", "spaces", ["id"])
    op.create_index("ix_spaces_distrito", "spaces", ["distrito"])
    op.create_index("ix_spaces_estado", "spaces", ["estado"])
    op.create_index("ix_spaces_anfitrion_id", "spaces", ["anfitrion_id"])

    op.create_table(
        "availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hora_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hora_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disponible", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_availability_space_id", "availability", ["space_id"])
    op.create_index("ix_availability_fecha", "availability", ["fecha"])

    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_photos_space_id", "photos", ["space_id"])


def downgrade() -> None:
    op.drop_table("photos")
    op.drop_table("availability")
    op.drop_table("spaces")
    op.execute("DROP TYPE space_status")
