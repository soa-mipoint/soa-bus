import asyncio
import json
import logging
import uuid
from datetime import datetime

import aio_pika
from aio_pika import ExchangeType
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.notification_log import NotificationLog
from app.notifications.email import EmailSendResult, send_email
from app.notifications.templates import render_booking_email, render_welcome_email

logger = logging.getLogger(__name__)

EXCHANGE_NAMES = ["user_events", "booking_events", "space_events", "payment_events"]


def _format_datetime(value: str) -> str:
    if not value:
        return "fecha no disponible"
    try:
        normalized = value.strip().replace("Z", "+00:00")
        if normalized.endswith(" UTC"):
            normalized = normalized[:-4]
        return datetime.fromisoformat(normalized).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


def _event_id(payload: dict, routing_key: str) -> str:
    if payload.get("event_id"):
        return str(payload["event_id"])
    if payload.get("booking_id"):
        return f"legacy:{routing_key}:{payload['booking_id']}"
    return f"generated:{routing_key}:{uuid.uuid4()}"


def _event_type(payload: dict, routing_key: str) -> str:
    return str(payload.get("event_type") or routing_key)


async def _send_with_log(payload: dict, routing_key: str, to: str, subject: str, html: str) -> EmailSendResult:
    event_id = _event_id(payload, routing_key)
    event_type = _event_type(payload, routing_key)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(NotificationLog).where(
                NotificationLog.event_id == event_id,
                NotificationLog.recipient_email == to,
                NotificationLog.event_type == event_type,
            )
        )
        log = result.scalar_one_or_none()
        if log and log.status in ("SENT", "PROCESSING"):
            logger.info("Notification skipped for duplicate event %s to %s", event_id, to)
            return EmailSendResult(success=True, provider_message_id=log.provider_message_id)

        if not log:
            log = NotificationLog(
                event_id=event_id,
                event_type=event_type,
                recipient_email=to,
                subject=subject,
                provider="resend",
                status="PROCESSING",
            )
            session.add(log)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.info("Notification skipped for concurrent duplicate event %s to %s", event_id, to)
                return EmailSendResult(success=True)
        else:
            log.subject = subject
            log.status = "PROCESSING"
            log.error_message = None
            await session.commit()

    send_result = await asyncio.to_thread(send_email, to, subject, html)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(NotificationLog).where(
                NotificationLog.event_id == event_id,
                NotificationLog.recipient_email == to,
                NotificationLog.event_type == event_type,
            )
        )
        log = result.scalar_one_or_none()
        if log:
            log.status = "SENT" if send_result.success else "FAILED"
            log.provider_message_id = send_result.provider_message_id
            log.error_message = send_result.error_message
            await session.commit()

    return send_result


class EventConsumer:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None

    async def connect(self) -> None:
        try:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=5)

            exchanges: dict[str, aio_pika.RobustExchange] = {}
            for name in EXCHANGE_NAMES:
                exchanges[name] = await self._channel.declare_exchange(
                    name, ExchangeType.TOPIC, durable=True
                )

            user_queue = await self._channel.declare_queue("notification-service.user-events", durable=True)
            await user_queue.bind(exchanges["user_events"], routing_key="user.registered")
            await user_queue.consume(self._handle_user_registered)

            booking_queue = await self._channel.declare_queue("notification-service.booking-events", durable=True)
            await booking_queue.bind(exchanges["booking_events"], routing_key="booking.created")
            await booking_queue.bind(exchanges["booking_events"], routing_key="booking.confirmed")
            await booking_queue.bind(exchanges["booking_events"], routing_key="booking.cancelled")
            await booking_queue.consume(self._handle_booking_event)

            logger.info("Event consumer started - listening to user_events + booking_events")
        except Exception as exc:
            logger.error("Event consumer connection failed: %s", exc)

    async def disconnect(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def _handle_user_registered(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=True):
            try:
                payload = json.loads(message.body)
                email = payload.get("email", "")
                nombre = str(payload.get("nombre", "Usuario"))
                logger.info("user.registered received - sending welcome email to %s", email)
                if not email:
                    logger.warning("user.registered missing email - email not sent")
                    return
                result = await _send_with_log(
                    payload,
                    "user.registered",
                    email,
                    "Tu cuenta en MiPoint ya esta lista",
                    render_welcome_email(nombre),
                )
                if not result.success:
                    logger.warning("user.registered email delivery failed for %s", email)
                    raise RuntimeError(result.error_message or "user.registered email delivery failed")
            except Exception as exc:
                logger.error("Error handling user.registered: %s", exc)
                raise

    async def _handle_booking_event(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=True):
            try:
                payload = json.loads(message.body)
                routing_key = message.routing_key
                logger.info(
                    "Booking event received: routing_key=%s event_id=%s codigo=%s",
                    routing_key,
                    payload.get("event_id"),
                    payload.get("codigo_reserva"),
                )

                if routing_key == "booking.created":
                    await self._notify_booking_created(payload, routing_key)
                elif routing_key == "booking.confirmed":
                    await self._notify_booking_confirmed(payload, routing_key)
                elif routing_key == "booking.cancelled":
                    await self._notify_booking_cancelled(payload, routing_key)
            except Exception as exc:
                logger.error("Error handling booking event: %s", exc)
                raise

    async def _notify_booking_created(self, payload: dict, routing_key: str) -> None:
        codigo = payload.get("codigo_reserva", "N/A")
        email = payload.get("cliente_email")
        if not email:
            logger.warning("booking.created missing cliente_email - email not sent for %s", codigo)
            return
        result = await _send_with_log(
            payload,
            routing_key,
            email,
            f"Reserva recibida - {codigo}",
            render_booking_email(
                title="Reserva recibida",
                greeting_name=str(payload.get("cliente_nombre") or "Usuario"),
                message="Recibimos tu solicitud de reserva. El anfitrion la revisara y te notificaremos cuando sea confirmada.",
                space_nombre=str(payload.get("space_nombre") or "espacio reservado"),
                codigo_reserva=str(payload.get("codigo_reserva", "N/A")),
                fecha_inicio=_format_datetime(str(payload.get("fecha_inicio", ""))),
                fecha_fin=_format_datetime(str(payload.get("fecha_fin", ""))),
                status_label="Pendiente de confirmacion",
                cta_label="Ver mi reserva",
            ),
        )
        if not result.success:
            logger.warning("booking.created email delivery failed for %s", codigo)
            raise RuntimeError(result.error_message or f"booking.created email delivery failed for {codigo}")

    async def _notify_booking_confirmed(self, payload: dict, routing_key: str) -> None:
        codigo = payload.get("codigo_reserva", "N/A")
        email = payload.get("cliente_email")
        if not email:
            logger.warning("booking.confirmed missing cliente_email - email not sent for %s", codigo)
            return
        result = await _send_with_log(
            payload,
            routing_key,
            email,
            f"Reserva confirmada - {codigo}",
            render_booking_email(
                title="Reserva confirmada",
                greeting_name=str(payload.get("cliente_nombre") or "Usuario"),
                message="Tu reserva fue confirmada correctamente. Ya puedes coordinar los detalles finales de tu evento con tranquilidad.",
                space_nombre=str(payload.get("space_nombre") or "espacio reservado"),
                codigo_reserva=str(payload.get("codigo_reserva", "N/A")),
                fecha_inicio=_format_datetime(str(payload.get("fecha_inicio", ""))),
                fecha_fin=_format_datetime(str(payload.get("fecha_fin", ""))),
                status_label="Confirmada",
                cta_label="Ver detalles",
            ),
        )
        if not result.success:
            logger.warning("booking.confirmed email delivery failed for %s", codigo)
            raise RuntimeError(result.error_message or f"booking.confirmed email delivery failed for {codigo}")

    async def _notify_booking_cancelled(self, payload: dict, routing_key: str) -> None:
        codigo = payload.get("codigo_reserva", "N/A")
        motivo = payload.get("motivo", "")
        email = payload.get("cliente_email")
        if not email:
            logger.warning("booking.cancelled missing cliente_email - email not sent for %s", codigo)
            return
        result = await _send_with_log(
            payload,
            routing_key,
            email,
            f"Reserva cancelada - {codigo}",
            render_booking_email(
                title="Reserva cancelada",
                greeting_name=str(payload.get("cliente_nombre") or "Usuario"),
                message="Tu reserva fue cancelada. Si necesitas otro espacio, puedes volver a buscar opciones disponibles en MiPoint.",
                space_nombre=str(payload.get("space_nombre") or "espacio reservado"),
                codigo_reserva=str(payload.get("codigo_reserva", "N/A")),
                fecha_inicio=_format_datetime(str(payload.get("fecha_inicio", ""))),
                fecha_fin=_format_datetime(str(payload.get("fecha_fin", ""))),
                status_label="Cancelada",
                cta_label="Buscar otro espacio",
                motivo=str(motivo) if motivo else None,
            ),
        )
        if not result.success:
            logger.warning("booking.cancelled email delivery failed for %s", codigo)
            raise RuntimeError(result.error_message or f"booking.cancelled email delivery failed for {codigo}")


event_consumer = EventConsumer()
