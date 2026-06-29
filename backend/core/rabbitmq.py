# core/rabbitmq.py
# RabbitMQ initialization helper
import asyncio
from common.a2a import A2AMessageBroker

a2aMessageBroker = A2AMessageBroker()

async def initialize_rabbitmq():
    """Initialize RabbitMQ connection and exchange"""
    try:
        await a2aMessageBroker.get_connection()
        await a2aMessageBroker.get_exchange()
        print("[RabbitMQ] Connection and exchange initialized")

        # clear all queues on startup
        channel = a2aMessageBroker._channel
        queue_names = ["Orchestrator", "Elicitation", "CDN", "Refinement", "Document", "User_Story"]  
        for name in queue_names:
            queue = await channel.declare_queue(name, durable=True)
            await queue.purge()
            print(f"[RabbitMQ] Purged: {name}")

    except Exception as e:
        print(f"[RabbitMQ] Error initializing: {e}")
        raise