import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmsSendResult:
    success: bool
    provider_message_id: str | None = None
    error_message: str | None = None


def send_sms(to: str, body: str) -> SmsSendResult:
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM_NUMBER]):
        logger.warning("Twilio not configured — SMS not sent to %s", to)
        return SmsSendResult(success=False, error_message="Twilio not configured")
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(body=body, from_=settings.TWILIO_FROM_NUMBER, to=to)
        logger.info("SMS sent to %s", to)
        return SmsSendResult(success=True, provider_message_id=getattr(message, "sid", None))
    except Exception as exc:
        logger.error("SMS send failed to %s: %s", to, exc)
        return SmsSendResult(success=False, error_message=str(exc))
