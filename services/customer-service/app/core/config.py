from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Customer Service"
    APP_VERSION: str = "1.0.0"

    DATABASE_URL: str = "postgresql+asyncpg://mipoint:mipoint_secret@localhost:5432/customers_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://mipoint:mipoint_secret@localhost:5672/"

    JWT_SECRET_KEY: str = "dev-secret-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_ISSUER: str = "mipoint-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
