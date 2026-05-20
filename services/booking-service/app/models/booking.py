import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    codigo_reserva = Column(String(20), unique=True, nullable=False, index=True)
    cliente_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    space_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    anfitrion_id = Column(UUID(as_uuid=True), nullable=False)
    fecha_inicio = Column(DateTime(timezone=True), nullable=False)
    fecha_fin = Column(DateTime(timezone=True), nullable=False)
    num_personas = Column(Integer, nullable=False)
    estado = Column(
        ENUM("PENDIENTE", "CONFIRMADA", "CANCELADA", "PAGADA", name="booking_status", create_type=False),
        nullable=False,
        default="PENDIENTE",
        index=True,
    )
    motivo_cancelacion = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    history = relationship("BookingStatusHistory", back_populates="booking", cascade="all, delete-orphan", order_by="BookingStatusHistory.created_at")


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    estado_anterior = Column(String(20), nullable=True)
    estado_nuevo = Column(String(20), nullable=False)
    nota = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    booking = relationship("Booking", back_populates="history")
