import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import CurrentUser, get_current_user, require_anfitrion
from app.core.config import settings
from app.core.database import get_db
from app.core.rabbitmq import rabbitmq_manager
from app.core.redis_client import get_redis
from app.models.space import Availability, Photo, Space
from app.schemas.space import (
    AvailabilityRangeResponse,
    CreateSpaceRequest,
    SpaceListResponse,
    SpaceResponse,
    UpdateStatusRequest,
)

router = APIRouter(prefix="/spaces", tags=["spaces"])


async def _get_space_or_404(space_id: UUID, db: AsyncSession) -> Space:
    result = await db.execute(
        select(Space).where(Space.id == space_id).options(
            selectinload(Space.photos),
            selectinload(Space.availability),
        )
    )
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    return space


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_space(
    payload: CreateSpaceRequest,
    user: CurrentUser = Depends(require_anfitrion),
    db: AsyncSession = Depends(get_db),
):
    space = Space(
        anfitrion_id=user.user_id,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        direccion=payload.direccion,
        distrito=payload.distrito,
        capacidad=payload.capacidad,
        precio_hora=payload.precio_hora,
        estado="PENDIENTE",
    )
    db.add(space)
    await db.flush()

    for idx, url in enumerate(payload.fotos):
        db.add(Photo(space_id=space.id, url=url, orden=idx))

    await db.commit()
    await db.refresh(space, ["photos", "availability"])

    await rabbitmq_manager.publish(
        "space_events",
        "space.created",
        {"space_id": str(space.id), "anfitrion_id": str(user.user_id), "nombre": space.nombre},
    )

    return SpaceResponse.model_validate(space)


@router.get("", response_model=SpaceListResponse)
async def search_spaces(
    fecha: datetime | None = Query(None, description="Fecha del evento (ISO 8601)"),
    capacidad: int | None = Query(None, ge=1),
    distrito: str | None = Query(None),
    precio_max: float | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"search:{fecha}:{capacidad}:{distrito}:{precio_max}:{page}:{size}"
    redis = await get_redis()
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    filters = [Space.estado == "ACTIVO"]
    if capacidad:
        filters.append(Space.capacidad >= capacidad)
    if distrito:
        filters.append(Space.distrito.ilike(f"%{distrito}%"))
    if precio_max:
        filters.append(Space.precio_hora <= precio_max)

    count_q = await db.execute(select(func.count()).select_from(Space).where(and_(*filters)))
    total = count_q.scalar_one()

    result = await db.execute(
        select(Space)
        .where(and_(*filters))
        .options(selectinload(Space.photos))
        .offset((page - 1) * size)
        .limit(size)
        .order_by(Space.created_at.desc())
    )
    spaces = result.scalars().all()

    response = SpaceListResponse(
        items=[SpaceResponse.model_validate(s) for s in spaces],
        total=total,
        page=page,
        size=size,
    )

    await redis.setex(cache_key, settings.SEARCH_CACHE_TTL, response.model_dump_json())
    return response


@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(space_id: UUID, db: AsyncSession = Depends(get_db)):
    return SpaceResponse.model_validate(await _get_space_or_404(space_id, db))


@router.put("/{space_id}/status", response_model=SpaceResponse)
async def update_status(
    space_id: UUID,
    payload: UpdateStatusRequest,
    user: CurrentUser = Depends(require_anfitrion),
    db: AsyncSession = Depends(get_db),
):
    space = await _get_space_or_404(space_id, db)

    if user.rol != "admin" and space.anfitrion_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your space")

    space.estado = payload.estado.value
    await db.commit()
    await db.refresh(space, ["photos"])

    routing_key = "space.activated" if payload.estado.value == "ACTIVO" else "space.deactivated"
    await rabbitmq_manager.publish(
        "space_events",
        routing_key,
        {"space_id": str(space.id), "anfitrion_id": str(space.anfitrion_id), "estado": space.estado},
    )

    return SpaceResponse.model_validate(space)


@router.get("/{space_id}/availability", response_model=AvailabilityRangeResponse)
async def get_availability(
    space_id: UUID,
    fecha_inicio: datetime = Query(...),
    fecha_fin: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await _get_space_or_404(space_id, db)

    result = await db.execute(
        select(Availability).where(
            and_(
                Availability.space_id == space_id,
                Availability.hora_inicio >= fecha_inicio,
                Availability.hora_fin <= fecha_fin,
            )
        ).order_by(Availability.hora_inicio)
    )
    slots = result.scalars().all()

    return AvailabilityRangeResponse(space_id=space_id, slots=slots)


@router.post("/{space_id}/availability/lock", include_in_schema=False)
async def lock_availability(
    space_id: UUID,
    booking_id: UUID,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint called by Booking Service to lock availability."""
    result = await db.execute(
        select(Availability).where(
            and_(
                Availability.space_id == space_id,
                Availability.hora_inicio >= fecha_inicio,
                Availability.hora_fin <= fecha_fin,
                Availability.disponible == True,  # noqa: E712
            )
        )
    )
    slots = result.scalars().all()

    for slot in slots:
        slot.disponible = False
        slot.booking_id = booking_id

    if not slots:
        slot = Availability(
            space_id=space_id,
            fecha=fecha_inicio,
            hora_inicio=fecha_inicio,
            hora_fin=fecha_fin,
            disponible=False,
            booking_id=booking_id,
        )
        db.add(slot)

    await db.commit()

    await rabbitmq_manager.publish(
        "space_events",
        "space.availability_updated",
        {"space_id": str(space_id), "booking_id": str(booking_id), "action": "locked"},
    )

    return {"status": "locked"}


@router.post("/{space_id}/availability/release", include_in_schema=False)
async def release_availability(
    space_id: UUID,
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint called by Booking Service to release availability."""
    result = await db.execute(
        select(Availability).where(
            and_(
                Availability.space_id == space_id,
                Availability.booking_id == booking_id,
            )
        )
    )
    slots = result.scalars().all()

    for slot in slots:
        slot.disponible = True
        slot.booking_id = None

    await db.commit()

    await rabbitmq_manager.publish(
        "space_events",
        "space.availability_updated",
        {"space_id": str(space_id), "booking_id": str(booking_id), "action": "released"},
    )

    return {"status": "released"}
