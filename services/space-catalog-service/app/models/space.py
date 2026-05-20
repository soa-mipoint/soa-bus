import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Space(Base):
    __tablename__ = "spaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    anfitrion_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    direccion = Column(String(500), nullable=False)
    distrito = Column(String(100), nullable=False, index=True)
    capacidad = Column(Integer, nullable=False)
    precio_hora = Column(Float, nullable=False)
    estado = Column(
        ENUM("ACTIVO", "INACTIVO", "PENDIENTE", name="space_status", create_type=False),
        nullable=False,
        default="PENDIENTE",
        index=True,
    )
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    availability = relationship("Availability", back_populates="space", cascade="all, delete-orphan")
    photos = relationship("Photo", back_populates="space", cascade="all, delete-orphan", order_by="Photo.orden")


class Availability(Base):
    __tablename__ = "availability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id = Column(UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha = Column(DateTime(timezone=True), nullable=False, index=True)
    hora_inicio = Column(DateTime(timezone=True), nullable=False)
    hora_fin = Column(DateTime(timezone=True), nullable=False)
    disponible = Column(Boolean, nullable=False, default=True)
    booking_id = Column(UUID(as_uuid=True), nullable=True)  # set when locked by a booking

    space = relationship("Space", back_populates="availability")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id = Column(UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    orden = Column(Integer, nullable=False, default=0)

    space = relationship("Space", back_populates="photos")
