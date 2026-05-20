from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Notification Service"
    APP_VERSION: str = "1.0.0"

    RABBITMQ_URL: str = "amqp://mipoint:mipoint_secret@localhost:5672/"

    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@mipoint.pe"

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
