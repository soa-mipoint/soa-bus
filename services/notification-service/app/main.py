import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.consumers.event_consumer import event_consumer
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s — ESB consumer mode...", settings.APP_NAME)
    await event_consumer.connect()
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)
    await event_consumer.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ESB consumer — no public API. Sends email (Resend) and SMS (Twilio) on domain events.",
    lifespan=lifespan,
)

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": "ESB consumer — no public API",
    }
