import random
import string
import asyncio
from datetime import datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rabbitmq import rabbitmq_manager
from app.core.redis_client import get_redis
from app.models.booking import Booking, BookingStatusHistory
from app.schemas.booking import (
    BookingListResponse,
    BookingResponse,
    CancelBookingRequest,
    ConfirmBookingRequest,
    CreateBookingRequest,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _generate_code() -> str:
    return "MIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def _get_booking_or_404(booking_id: UUID, db: AsyncSession) -> Booking:
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.history))
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


async def _acquire_availability_lock(redis, space_id: UUID, fecha_inicio: datetime, fecha_fin: datetime) -> str | None:
    """Redis distributed lock to prevent double-booking. Returns lock token or None."""
    lock_key = f"lock:space:{space_id}:{fecha_inicio.isoformat()}:{fecha_fin.isoformat()}"
    lock_token = "".join(random.choices(string.ascii_letters, k=16))
    acquired = await redis.set(lock_key, lock_token, nx=True, ex=settings.LOCK_TTL_SECONDS)
    return lock_token if acquired else None


async def _release_lock(redis, space_id: UUID, fecha_inicio: datetime, fecha_fin: datetime, token: str) -> None:
    lock_key = f"lock:space:{space_id}:{fecha_inicio.isoformat()}:{fecha_fin.isoformat()}"
    stored = await redis.get(lock_key)
    if stored == token:
        await redis.delete(lock_key)


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: CreateBookingRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()

    # Acquire distributed lock — prevents concurrent double-booking for same slot
    lock_token = await _acquire_availability_lock(
        redis, payload.space_id, payload.fecha_inicio, payload.fecha_fin
    )
    if not lock_token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Space is being reserved by another user. Try again in a moment.",
        )

    if settings.TEST_DELAY_AFTER_LOCK_SECONDS > 0:
        await asyncio.sleep(settings.TEST_DELAY_AFTER_LOCK_SECONDS)

    try:
        booking = Booking(
            codigo_reserva=_generate_code(),
            cliente_id=user.user_id,
            space_id=payload.space_id,
            anfitrion_id=payload.anfitrion_id,
            fecha_inicio=payload.fecha_inicio,
            fecha_fin=payload.fecha_fin,
            num_personas=payload.num_personas,
            estado="PENDIENTE",
        )
        db.add(booking)

        history = BookingStatusHistory(
            booking=booking,
            estado_anterior=None,
            estado_nuevo="PENDIENTE",
            nota="Booking created",
        )
        db.add(history)
        await db.commit()
        await db.refresh(booking, ["history"])

    finally:
        await _release_lock(redis, payload.space_id, payload.fecha_inicio, payload.fecha_fin, lock_token)

    await rabbitmq_manager.publish(
        "booking_events",
        "booking.created",
        {
            "booking_id": str(booking.id),
            "codigo_reserva": booking.codigo_reserva,
            "cliente_id": str(user.user_id),
            "space_id": str(payload.space_id),
            "anfitrion_id": str(payload.anfitrion_id),
            "fecha_inicio": payload.fecha_inicio.isoformat(),
            "fecha_fin": payload.fecha_fin.isoformat(),
        },
    )

    return BookingResponse.model_validate(booking)


@router.put("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking(
    booking_id: UUID,
    payload: ConfirmBookingRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_booking_or_404(booking_id, db)

    if booking.estado != "PENDIENTE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot confirm booking in '{booking.estado}' state")

    if user.rol not in ("anfitrion", "admin") and str(booking.anfitrion_id) != str(user.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can confirm this booking")

    history = BookingStatusHistory(
        booking_id=booking.id,
        estado_anterior=booking.estado,
        estado_nuevo="CONFIRMADA",
        nota=payload.nota,
    )
    booking.estado = "CONFIRMADA"
    db.add(history)
    await db.commit()
    await db.refresh(booking, ["history"])

    # Notify Space Catalog to lock availability
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{settings.SPACE_CATALOG_URL}/api/v1/spaces/{booking.space_id}/availability/lock",
                params={
                    "booking_id": str(booking.id),
                    "fecha_inicio": booking.fecha_inicio.isoformat(),
                    "fecha_fin": booking.fecha_fin.isoformat(),
                },
                timeout=10,
            )
        except Exception:
            pass  # ESB event also triggers this

    await rabbitmq_manager.publish(
        "booking_events",
        "booking.confirmed",
        {
            "booking_id": str(booking.id),
            "codigo_reserva": booking.codigo_reserva,
            "cliente_id": str(booking.cliente_id),
            "space_id": str(booking.space_id),
            "anfitrion_id": str(booking.anfitrion_id),
            "fecha_inicio": booking.fecha_inicio.isoformat(),
            "fecha_fin": booking.fecha_fin.isoformat(),
        },
    )

    return BookingResponse.model_validate(booking)


@router.put("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID,
    payload: CancelBookingRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_booking_or_404(booking_id, db)

    if booking.estado in ("CANCELADA", "PAGADA"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel booking in '{booking.estado}' state")

    is_owner = str(booking.cliente_id) == str(user.user_id)
    is_host = str(booking.anfitrion_id) == str(user.user_id)
    if not (is_owner or is_host or user.rol == "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this booking")

    history = BookingStatusHistory(
        booking_id=booking.id,
        estado_anterior=booking.estado,
        estado_nuevo="CANCELADA",
        nota=payload.motivo,
    )
    booking.estado = "CANCELADA"
    booking.motivo_cancelacion = payload.motivo
    db.add(history)
    await db.commit()
    await db.refresh(booking, ["history"])

    # Release availability lock if it was confirmed
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{settings.SPACE_CATALOG_URL}/api/v1/spaces/{booking.space_id}/availability/release",
                params={"booking_id": str(booking.id)},
                timeout=10,
            )
        except Exception:
            pass

    await rabbitmq_manager.publish(
        "booking_events",
        "booking.cancelled",
        {
            "booking_id": str(booking.id),
            "codigo_reserva": booking.codigo_reserva,
            "cliente_id": str(booking.cliente_id),
            "space_id": str(booking.space_id),
            "anfitrion_id": str(booking.anfitrion_id),
            "motivo": payload.motivo,
        },
    )

    return BookingResponse.model_validate(booking)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_booking_or_404(booking_id, db)

    is_owner = str(booking.cliente_id) == str(user.user_id)
    is_host = str(booking.anfitrion_id) == str(user.user_id)
    if not (is_owner or is_host or user.rol == "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return BookingResponse.model_validate(booking)


@router.get("/client/{cliente_id}", response_model=BookingListResponse)
async def get_client_bookings(
    cliente_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if str(user.user_id) != str(cliente_id) and user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    count_result = await db.execute(select(func.count()).where(Booking.cliente_id == cliente_id))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Booking)
        .where(Booking.cliente_id == cliente_id)
        .options(selectinload(Booking.history))
        .order_by(Booking.created_at.desc())
    )
    bookings = result.scalars().all()

    return BookingListResponse(
        items=[BookingResponse.model_validate(b) for b in bookings],
        total=total,
    )
