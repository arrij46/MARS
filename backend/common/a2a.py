import os
import json
import asyncio
from pydantic import BaseModel
from typing import Dict, Any, Callable
import aio_pika


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@127.0.0.1/")
EXCHANGE_NAME = "agents-exchange"

# Global connection management
_connection: aio_pika.RobustConnection | None = None
_channel: aio_pika.RobustChannel | None = None
_exchange: aio_pika.Exchange | None = None


class A2AMessage(BaseModel):

    sender: str
    receiver: str
    type: str
    payload: Dict[str, Any]
    conv_id: str

class A2AMessageBroker:
    def __init__(self):
        self.rabbitmq_url = RABBITMQ_URL
        self.exchange_name = EXCHANGE_NAME

        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._exchange: aio_pika.Exchange | None = None
    
    async def get_connection(self) -> aio_pika.RobustConnection:
        """Get or create RabbitMQ connection"""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
        return self._connection

    async def get_channel(self) -> aio_pika.RobustChannel:
        """Get or create RabbitMQ channel"""
        await self.get_connection()
        if self._channel is None or self._channel.is_closed:
            self._channel = await self._connection.channel()
        return self._channel

    async def get_exchange(self) -> aio_pika.Exchange:
        """Get or create direct exchange"""
        await self.get_channel()
        if self._exchange is None:
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
        return self._exchange

    async def publish_message(self, routing_key: str, message: dict):
        """Publish A2A message to RabbitMQ"""
        exchange = await self.get_exchange()
        message_body = json.dumps(message).encode()

        await exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key,
        )
        
    async def consume_queue(self, queue_name: str, handler: Callable):
        """Consume messages from a specific queue"""
        channel = await self.get_channel()
        exchange = await self.get_exchange()

        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(exchange, routing_key=queue_name)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        payload = json.loads(message.body.decode())
                        await handler(payload)
                    except Exception as e:
                        print(f"[A2A] Error processing message: {e}")