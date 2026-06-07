import json
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rabbitmq import rabbitmq_manager
from app.core.redis_client import get_redis
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Profile, User
from app.schemas.user import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


def _event_metadata(event_type: str) -> dict[str, str]:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_user_event(user: User, event_type: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        **_event_metadata(event_type),
        "user_id": str(user.id),
        "email": user.email,
        "nombre": user.nombre,
        "rol": user.rol,
    }
    if extra:
        payload.update(extra)
    return payload


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        nombre=payload.nombre,
        rol=payload.rol.value,
    )
    profile = Profile(user=user)
    db.add(user)
    db.add(profile)
    await db.commit()
    await db.refresh(user, ["profile"])

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "nombre": user.nombre,
        "rol": user.rol,
    })

    await rabbitmq_manager.publish(
        "user_events",
        "user.registered",
        _build_user_event(user, "user.registered"),
    )

    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == payload.email).options(selectinload(User.profile))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "nombre": user.nombre,
        "rol": user.rol,
    })

    # Store session in Redis for potential revocation
    redis = await get_redis()
    session_key = f"session:{str(user.id)}"
    await redis.setex(
        session_key,
        settings.JWT_EXPIRE_MINUTES * 60,
        json.dumps({
            "user_id": str(user.id),
            "email": user.email,
            "nombre": user.nombre,
            "rol": user.rol,
        }),
    )

    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/logout", response_model=MessageResponse)
async def logout(user: User = Depends(get_current_user)):
    redis = await get_redis()
    await redis.delete(f"session:{str(user.id)}")
    return MessageResponse(message="Logged out successfully")


@router.get("/profile", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.nombre is not None:
        user.nombre = payload.nombre

    if user.profile is None:
        user.profile = Profile(user_id=user.id)
        db.add(user.profile)

    if payload.phone is not None:
        user.profile.phone = payload.phone
    if payload.avatar_url is not None:
        user.profile.avatar_url = payload.avatar_url
    if payload.bio is not None:
        user.profile.bio = payload.bio

    await db.commit()
    await db.refresh(user, ["profile"])

    await rabbitmq_manager.publish(
        "user_events",
        "user.updated",
        _build_user_event(user, "user.updated"),
    )

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.rol != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.profile))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)
