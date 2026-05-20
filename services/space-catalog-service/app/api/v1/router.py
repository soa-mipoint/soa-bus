from fastapi import APIRouter

from app.api.v1.routes.spaces import router as spaces_router

api_router = APIRouter()
api_router.include_router(spaces_router)
