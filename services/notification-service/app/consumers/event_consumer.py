import json
import logging

import aio_pika
from aio_pika import ExchangeType

from app.core.config import settings
from app.notifications.email import send_email

logger = logging.getLogger(__name__)

EXCHANGE_NAMES = ["user_events", "booking_events", "space_events", "payment_events"]


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

            # Queue for user events
            user_queue = await self._channel.declare_queue("notification-service.user-events", durable=True)
            await user_queue.bind(exchanges["user_events"], routing_key="user.registered")
            await user_queue.consume(self._handle_user_registered)

            # Queue for booking events
            booking_queue = await self._channel.declare_queue("notification-service.booking-events", durable=True)
            await booking_queue.bind(exchanges["booking_events"], routing_key="booking.created")
            await booking_queue.bind(exchanges["booking_events"], routing_key="booking.confirmed")
            await booking_queue.bind(exchanges["booking_events"], routing_key="booking.cancelled")
            await booking_queue.consume(self._handle_booking_event)

            logger.info("Event consumer started — listening to user_events + booking_events")
        except Exception as exc:
            logger.error("Event consumer connection failed: %s", exc)

    async def disconnect(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def _handle_user_registered(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process():
            try:
                payload = json.loads(message.body)
                email = payload.get("email", "")
                nombre = payload.get("nombre", "Usuario")
                logger.info("user.registered received — sending welcome email to %s", email)
                send_email(
                    to=email,
                    subject="¡Bienvenido a MiPoint!",
                    html=f"""
                    <h2>Hola {nombre}, ¡bienvenido a MiPoint!</h2>
                    <p>Tu cuenta ha sido creada exitosamente. Ya puedes buscar y reservar espacios para tus eventos.</p>
                    <p>— El equipo de MiPoint</p>
                    """,
                )
            except Exception as exc:
                logger.error("Error handling user.registered: %s", exc)

    async def _handle_booking_event(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process():
            try:
                payload = json.loads(message.body)
                routing_key = message.routing_key
                logger.info("Booking event received: %s — %s", routing_key, payload)

                if routing_key == "booking.created":
                    await self._notify_booking_created(payload)
                elif routing_key == "booking.confirmed":
                    await self._notify_booking_confirmed(payload)
                elif routing_key == "booking.cancelled":
                    await self._notify_booking_cancelled(payload)
            except Exception as exc:
                logger.error("Error handling booking event: %s", exc)

    async def _notify_booking_created(self, payload: dict) -> None:
        codigo = payload.get("codigo_reserva", "N/A")
        fecha_inicio = payload.get("fecha_inicio", "")
        fecha_fin = payload.get("fecha_fin", "")
        # In production, fetch client email from Customer Service
        # Here we log and use email from payload if available
        logger.info(
            "BOOKING CREATED — codigo: %s, %s → %s",
            codigo, fecha_inicio, fecha_fin,
        )

    async def _notify_booking_confirmed(self, payload: dict) -> None:
        codigo = payload.get("codigo_reserva", "N/A")
        logger.info("BOOKING CONFIRMED — codigo: %s. Notifying client.", codigo)

    async def _notify_booking_cancelled(self, payload: dict) -> None:
        codigo = payload.get("codigo_reserva", "N/A")
        motivo = payload.get("motivo", "")
        logger.info("BOOKING CANCELLED — codigo: %s, motivo: %s", codigo, motivo)


event_consumer = EventConsumer()
