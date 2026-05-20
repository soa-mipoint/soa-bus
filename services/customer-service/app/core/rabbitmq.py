import json
import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode

from app.core.config import settings

logger = logging.getLogger(__name__)

EXCHANGE_NAMES = ["user_events", "booking_events", "space_events", "payment_events"]


class RabbitMQManager:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._exchanges: dict[str, aio_pika.RobustExchange] = {}

    async def connect(self) -> None:
        try:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)
            for name in EXCHANGE_NAMES:
                self._exchanges[name] = await self._channel.declare_exchange(
                    name, ExchangeType.TOPIC, durable=True
                )
            logger.info("RabbitMQ connected — exchanges declared")
        except Exception as exc:
            logger.error("RabbitMQ connection failed: %s", exc)

    async def disconnect(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ disconnected")

    async def publish(self, exchange: str, routing_key: str, payload: dict[str, Any]) -> None:
        if exchange not in self._exchanges:
            logger.error("Exchange '%s' not found", exchange)
            return
        try:
            body = json.dumps(payload, default=str).encode()
            await self._exchanges[exchange].publish(
                Message(body=body, delivery_mode=DeliveryMode.PERSISTENT),
                routing_key=routing_key,
            )
            logger.info("Published → %s / %s", exchange, routing_key)
        except Exception as exc:
            logger.error("Publish failed (%s/%s): %s", exchange, routing_key, exc)


rabbitmq_manager = RabbitMQManager()
