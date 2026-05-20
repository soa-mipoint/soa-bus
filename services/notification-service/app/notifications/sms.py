import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_sms(to: str, body: str) -> bool:
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM_NUMBER]):
        logger.warning("Twilio not configured — SMS not sent to %s", to)
        return False
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(body=body, from_=settings.TWILIO_FROM_NUMBER, to=to)
        logger.info("SMS sent to %s", to)
        return True
    except Exception as exc:
        logger.error("SMS send failed to %s: %s", to, exc)
        return False
