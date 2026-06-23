from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import decode_token

bearer_scheme = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: UUID, email: str, nombre: str, phone: str | None, rol: str):
        self.user_id = user_id
        self.email = email
        self.nombre = nombre
        self.phone = phone
        self.rol = rol


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return CurrentUser(
            user_id=UUID(user_id_str),
            email=payload.get("email", ""),
            nombre=payload.get("nombre", "Usuario"),
            phone=payload.get("phone"),
            rol=payload.get("rol", "cliente"),
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid or expired")
