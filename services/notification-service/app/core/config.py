from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Notification Service"
    APP_VERSION: str = "1.0.0"

    RABBITMQ_URL: str = "amqp://mipoint:mipoint_secret@localhost:5672/"
    DATABASE_URL: str = "postgresql+asyncpg://mipoint:mipoint_secret@localhost:5432/notifications_db"

    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "onboarding@resend.dev"

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
