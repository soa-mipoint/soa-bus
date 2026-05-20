from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Space Catalog Service"
    APP_VERSION: str = "1.0.0"

    DATABASE_URL: str = "postgresql+asyncpg://mipoint:mipoint_secret@localhost:5432/catalog_db"
    REDIS_URL: str = "redis://localhost:6379/1"
    RABBITMQ_URL: str = "amqp://mipoint:mipoint_secret@localhost:5672/"

    JWT_SECRET_KEY: str = "dev-secret-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "mipoint-key"

    GOOGLE_MAPS_API_KEY: str = ""

    SEARCH_CACHE_TTL: int = 300  # 5 minutes

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
