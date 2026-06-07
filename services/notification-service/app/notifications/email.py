import logging
from dataclasses import dataclass

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailSendResult:
    success: bool
    provider_message_id: str | None = None
    error_message: str | None = None


def send_email(to: str, subject: str, html: str) -> EmailSendResult:
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured; email not sent to %s", to)
        return EmailSendResult(success=False, error_message="RESEND_API_KEY not configured")
    try:
        resend.api_key = settings.RESEND_API_KEY
        response = resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent to %s - %s", to, subject)
        provider_message_id = response.get("id") if isinstance(response, dict) else None
        return EmailSendResult(success=True, provider_message_id=provider_message_id)
    except Exception as exc:
        logger.error("Email send failed to %s: %s", to, exc)
        return EmailSendResult(success=False, error_message=str(exc))
