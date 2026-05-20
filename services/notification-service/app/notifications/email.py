import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html: str) -> bool:
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured — email not sent to %s", to)
        return False
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent to %s — %s", to, subject)
        return True
    except Exception as exc:
        logger.error("Email send failed to %s: %s", to, exc)
        return False
