import logging
from contextlib import asynccontextmanager

import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.rabbitmq import rabbitmq_manager
from app.core.redis_client import close_redis
import app.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s...", settings.APP_NAME)
    async with engine.begin() as conn:
        await conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE space_status AS ENUM ('ACTIVO', 'INACTIVO', 'PENDIENTE');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")
    await rabbitmq_manager.connect()
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)
    await rabbitmq_manager.disconnect()
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Catálogo de espacios para eventos. Dominio: espacios, disponibilidad, fotos.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
