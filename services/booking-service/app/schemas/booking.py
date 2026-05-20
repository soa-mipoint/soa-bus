from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator


class BookingStatus(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    PAGADA = "PAGADA"


class StatusHistoryResponse(BaseModel):
    estado_anterior: str | None
    estado_nuevo: str
    nota: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateBookingRequest(BaseModel):
    space_id: UUID
    anfitrion_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    num_personas: int

    @field_validator("num_personas")
    @classmethod
    def personas_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("num_personas must be positive")
        return v

    @field_validator("fecha_fin")
    @classmethod
    def fin_after_inicio(cls, v: datetime, info) -> datetime:
        inicio = info.data.get("fecha_inicio")
        if inicio and v <= inicio:
            raise ValueError("fecha_fin must be after fecha_inicio")
        return v


class ConfirmBookingRequest(BaseModel):
    nota: str | None = None


class CancelBookingRequest(BaseModel):
    motivo: str


class BookingResponse(BaseModel):
    id: UUID
    codigo_reserva: str
    cliente_id: UUID
    space_id: UUID
    anfitrion_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    num_personas: int
    estado: BookingStatus
    motivo_cancelacion: str | None
    created_at: datetime
    history: list[StatusHistoryResponse] = []

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int
