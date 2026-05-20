from fastapi import APIRouter

from app.api.v1.routes.bookings import router as bookings_router

api_router = APIRouter()
api_router.include_router(bookings_router)
