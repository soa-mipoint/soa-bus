from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class UserRole(str, Enum):
    cliente = "cliente"
    anfitrion = "anfitrion"
    admin = "admin"


class RegisterRequest(BaseModel):
    nombre: str
    email: EmailStr
    phone: str
    password: str
    rol: UserRole = UserRole.cliente

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("phone")
    @classmethod
    def phone_e164(cls, v: str) -> str:
        if not v.startswith("+") or not v[1:].isdigit() or not 8 <= len(v[1:]) <= 15 or v[1] == "0":
            raise ValueError("Phone must be in E.164 format, e.g. +51999999999")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    nombre: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    bio: str | None = None

    @field_validator("phone")
    @classmethod
    def phone_e164(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("+") or not v[1:].isdigit() or not 8 <= len(v[1:]) <= 15 or v[1] == "0":
            raise ValueError("Phone must be in E.164 format, e.g. +51999999999")
        return v


class ProfileResponse(BaseModel):
    phone: str | None = None
    avatar_url: str | None = None
    bio: str | None = None

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: UUID
    email: str
    nombre: str
    rol: UserRole
    created_at: datetime
    profile: ProfileResponse | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
