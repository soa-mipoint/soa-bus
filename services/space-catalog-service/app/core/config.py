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
    INTERNAL_API_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000"

    GOOGLE_MAPS_API_KEY: str = ""

    SEARCH_CACHE_TTL: int = 300  # 5 minutes

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
