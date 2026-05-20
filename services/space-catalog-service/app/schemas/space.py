from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator


class SpaceStatus(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    PENDIENTE = "PENDIENTE"


class PhotoResponse(BaseModel):
    id: UUID
    url: str
    orden: int

    model_config = {"from_attributes": True}


class AvailabilityResponse(BaseModel):
    id: UUID
    fecha: datetime
    hora_inicio: datetime
    hora_fin: datetime
    disponible: bool

    model_config = {"from_attributes": True}


class CreateSpaceRequest(BaseModel):
    nombre: str
    descripcion: str | None = None
    direccion: str
    distrito: str
    capacidad: int
    precio_hora: float
    fotos: list[str] = []

    @field_validator("capacidad")
    @classmethod
    def capacidad_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Capacidad must be positive")
        return v

    @field_validator("precio_hora")
    @classmethod
    def precio_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Precio must be positive")
        return v


class UpdateStatusRequest(BaseModel):
    estado: SpaceStatus


class SpaceResponse(BaseModel):
    id: UUID
    anfitrion_id: UUID
    nombre: str
    descripcion: str | None
    direccion: str
    distrito: str
    capacidad: int
    precio_hora: float
    estado: SpaceStatus
    lat: float | None
    lng: float | None
    created_at: datetime
    photos: list[PhotoResponse] = []

    model_config = {"from_attributes": True}


class SpaceListResponse(BaseModel):
    items: list[SpaceResponse]
    total: int
    page: int
    size: int


class AvailabilityRangeResponse(BaseModel):
    space_id: UUID
    slots: list[AvailabilityResponse]
